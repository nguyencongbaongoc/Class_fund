/**
 * HtmlCapture — manages cached DOM-to-canvas snapshots for individual elements.
 *
 * Uses the `html-to-image` library to rasterise DOM nodes into
 * canvas-ready images. The library handles style inlining, font
 * embedding, canvas/image conversion and all the SVG-foreignObject
 * plumbing internally.
 *
 * Static elements are captured once and cached. Elements with the
 * `data-dynamic` attribute are re-captured every frame.
 */
import { toCanvas } from 'html-to-image';

interface CacheEntry {
	canvas: HTMLCanvasElement;
	w: number;
	h: number;
}

/**
 * Document-level cache for the prefetched + embedded @font-face blocks,
 * shared across every LiquidGlass instance on the page. The first call
 * kicks off the fetch + base64 inlining; every subsequent call returns
 * the same Promise. Cleared via `invalidateFontEmbedCache()`.
 */
let _sharedFontBlocks: Promise<EmbeddedFontBlock[]> | null = null;

/**
 * Discard the shared font-embed cache so the next prefetch rebuilds
 * it from scratch. Useful when stylesheets are added at runtime.
 */
export function invalidateFontEmbedCache(): void {
	_sharedFontBlocks = null;
}

/** A @font-face block that has already been fetched + base64-inlined. */
interface EmbeddedFontBlock {
	/** The full @font-face CSS text with data-URL src. */
	css: string;
	/** Normalised (lowercase, unquoted) font-family name. */
	family: string;
	/** Raw font-weight descriptor, e.g. "400" or "100 900". */
	weight: string;
	/** Raw font-style descriptor, e.g. "normal" or "italic". */
	style: string;
	/** Parsed unicode-range codepoint ranges, or null = all codepoints. */
	unicodeRanges: Array<[number, number]> | null;
}

// ─── @font-face descriptor parsing helpers ───

function parseFontFamily(block: string): string {
	const m = block.match(/font-family\s*:\s*(['"]?)([^;'"]+)\1/i);
	return m ? m[2].trim() : '';
}

function parseFontWeight(block: string): string {
	const m = block.match(/font-weight\s*:\s*([^;]+)/i);
	return m ? m[1].trim() : '400';
}

function parseFontStyle(block: string): string {
	const m = block.match(/font-style\s*:\s*([^;]+)/i);
	return m ? m[1].trim() : 'normal';
}

function parseUnicodeRange(block: string): Array<[number, number]> | null {
	const m = block.match(/unicode-range\s*:\s*([^;]+)/i);
	if (!m) return null;
	const ranges: Array<[number, number]> = [];
	for (const part of m[1].split(',')) {
		const trimmed = part.trim();
		const rangeMatch = trimmed.match(/U\+([0-9A-Fa-f]+)(?:-([0-9A-Fa-f]+))?/);
		if (!rangeMatch) continue;
		const start = parseInt(rangeMatch[1], 16);
		const end = rangeMatch[2] ? parseInt(rangeMatch[2], 16) : start;
		ranges.push([start, end]);
	}
	return ranges.length > 0 ? ranges : null;
}

function weightMatches(descriptor: string, target: string): boolean {
	const parts = descriptor.split(/\s+/).map(Number);
	const t = Number(target) || 400;
	if (parts.length >= 2) {
		return t >= parts[0] && t <= parts[1];
	}
	return parts[0] === t;
}

function textMatchesUnicodeRange(
	text: string,
	ranges: Array<[number, number]>,
): boolean {
	for (let i = 0; i < text.length; i++) {
		const cp = text.codePointAt(i)!;
		for (const [lo, hi] of ranges) {
			if (cp >= lo && cp <= hi) return true;
		}
		if (cp > 0xFFFF) i++;
	}
	return false;
}

interface FontUsage {
	family: string;
	weight: string;
	style: string;
	text: string;
}

function collectFontUsage(element: HTMLElement): FontUsage[] {
	const indexMap = new Map<string, number>();
	const fonts: FontUsage[] = [];

	function walk(node: Node): void {
		if (node.nodeType === 3) {
			const content = node.textContent || '';
			if (content.trim() === '') return;
			const parent = node.parentElement;
			if (!parent) return;
			const style = getComputedStyle(parent);
			const weight = style.fontWeight;
			const fontStyle = style.fontStyle;
			for (const raw of style.fontFamily.split(',')) {
				const family = raw.replace(/['"]/g, '').trim().toLowerCase();
				const key = `${family}|${weight}|${fontStyle}`;
				const idx = indexMap.get(key);
				if (idx !== undefined) {
					fonts[idx].text += content;
				} else {
					indexMap.set(key, fonts.length);
					fonts.push({ family, weight, style: fontStyle, text: content });
				}
			}
		} else if (node.nodeType === 1) {
			const el = node as HTMLElement;
			for (let i = 0; i < el.childNodes.length; i++) {
				walk(el.childNodes[i]);
			}
		}
	}

	walk(element);
	return fonts;
}

function filterFontBlocksForElement(
	blocks: EmbeddedFontBlock[],
	element: HTMLElement,
): EmbeddedFontBlock[] {
	const usages = collectFontUsage(element);
	if (usages.length === 0) return [];

	return blocks.filter((block) => {
		const matchingUsages = usages.filter((u) => {
			if (u.family !== block.family) return false;
			const styleOk = block.style === u.style
				|| (block.style === 'normal' && u.style === 'normal');
			return styleOk && weightMatches(block.weight, u.weight);
		});
		if (matchingUsages.length === 0) return false;

		if (block.unicodeRanges) {
			const hasMatch = matchingUsages.some(
				(u) => u.text.length > 0
					&& textMatchesUnicodeRange(u.text, block.unicodeRanges!),
			);
			if (!hasMatch) return false;
		}

		return true;
	});
}

async function fetchWithTimeout(url: string, timeoutMs = 2000): Promise<Response> {
	const controller = new AbortController();
	const id = setTimeout(() => controller.abort(), timeoutMs);
	try {
		const response = await fetch(url, { signal: controller.signal });
		clearTimeout(id);
		return response;
	} catch (e) {
		clearTimeout(id);
		throw e;
	}
}

async function fetchAsDataUrl(url: string): Promise<string | null> {
	try {
		const res = await fetchWithTimeout(url, 2000);
		if (!res.ok) return null;
		const blob = await res.blob();
		return new Promise<string>((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = () => resolve(reader.result as string);
			reader.onerror = reject;
			reader.readAsDataURL(blob);
		});
	} catch {
		return null;
	}
}

async function buildFontBlocks(): Promise<EmbeddedFontBlock[]> {
	const fontFaceRules: string[] = [];

	const links = Array.from(
		document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]'),
	);
	for (const link of links) {
		if (!link.href) continue;
		try {
			const res = await fetchWithTimeout(link.href, 2000);
			if (!res.ok) continue;
			const cssText = await res.text();
			const sheet = new CSSStyleSheet();
			await sheet.replace(cssText);
			for (const rule of sheet.cssRules) {
				if (rule.type === CSSRule.FONT_FACE_RULE) {
					fontFaceRules.push(rule.cssText);
				}
			}
		} catch {
			// Network error, CORS blocked, or timeout — skip.
		}
	}

	for (const sheet of Array.from(document.styleSheets)) {
		if (sheet.href) continue;
		try {
			for (const rule of Array.from(sheet.cssRules || [])) {
				if (rule.type === CSSRule.FONT_FACE_RULE) {
					fontFaceRules.push(rule.cssText);
				}
			}
		} catch {
			// SecurityError — skip.
		}
	}

	const loadedFamilies = new Set<string>();
	if (document.fonts) {
		for (const ff of document.fonts) {
			if (ff.status === 'loaded') {
				loadedFamilies.add(
					ff.family.replace(/['"]/g, '').trim().toLowerCase(),
				);
			}
		}
	}
	const candidates = loadedFamilies.size > 0
		? fontFaceRules.filter((r) => loadedFamilies.has(parseFontFamily(r).toLowerCase()))
		: fontFaceRules;

	const embedded = await Promise.all(
		candidates.map(async (ruleText) => {
			const urlRegex = /url\(\s*['"]?([^'")\s]+)['"]?\s*\)/g;
			const urlMatches = Array.from(ruleText.matchAll(urlRegex));
			let css = ruleText;
			for (const m of urlMatches) {
				const url = m[1];
				if (url.startsWith('data:')) continue;
				const dataUrl = await fetchAsDataUrl(url);
				if (dataUrl) {
					css = css.replace(m[0], `url(${dataUrl})`);
				}
			}
			return {
				css,
				family: parseFontFamily(ruleText).toLowerCase(),
				weight: parseFontWeight(ruleText),
				style: parseFontStyle(ruleText),
				unicodeRanges: parseUnicodeRange(ruleText),
			} satisfies EmbeddedFontBlock;
		}),
	);

	return embedded;
}

export class HtmlCapture {
	readonly root: HTMLElement;
	readonly cache: Map<HTMLElement, CacheEntry>;
	dpr: number;
	private readonly _capturing = new Set<HTMLElement>();
	onCacheUpdate: ((element: HTMLElement) => void) | null = null;
	private _fontBlocks: EmbeddedFontBlock[] = [];

	constructor(root: HTMLElement) {
		this.root = root;
		this.cache = new Map();
		this.dpr = 1;
	}

	async prefetchFontEmbedCSS(): Promise<void> {
		if (!_sharedFontBlocks) {
			_sharedFontBlocks = buildFontBlocks();
		}
		try {
			this._fontBlocks = await _sharedFontBlocks;
		} catch {
			this._fontBlocks = [];
		}
	}

	fontEmbedCSSForElement(element: HTMLElement): string {
		if (this._fontBlocks.length === 0) return '';
		const relevant = filterFontBlocksForElement(this._fontBlocks, element);
		return relevant.map((b) => b.css).join('\n');
	}

	resize(dpr = 1): void {
		this.dpr = dpr;
		this.cache.clear();
	}

	async captureElement(element: HTMLElement, force = false): Promise<void> {
		const rect = element.getBoundingClientRect();
		const cssW = rect.width;
		const cssH = rect.height;
		const w = Math.round(cssW * this.dpr);
		const h = Math.round(cssH * this.dpr);

		if (w <= 0 || h <= 0) {
			this.cache.delete(element);
			return;
		}

		const cached = this.cache.get(element);
		const cacheIsFresh = !!cached
			&& cached.canvas.width > 0
			&& cached.canvas.height > 0
			&& Math.abs(cached.w - w) < 0.5
			&& Math.abs(cached.h - h) < 0.5;

		if (!force && cacheIsFresh) return;

		if (this._capturing.has(element)) return;

		if (element.tagName === 'CANVAS') {
			return;
		}

		this._capturing.add(element);
		try {
			await this._captureWithHtmlToImage(element, w, h, cssW, cssH);
		} finally {
			this._capturing.delete(element);
		}
	}

	drawCachedElement(
		element: HTMLElement,
		targetCtx: CanvasRenderingContext2D,
		x: number,
		y: number,
		w: number,
		h: number,
	): boolean {
		const cached = this.cache.get(element);
		if (!cached) return false;
		if (cached.canvas.width <= 0 || cached.canvas.height <= 0) {
			this.cache.delete(element);
			return false;
		}
		targetCtx.drawImage(cached.canvas, x, y, w, h);
		return true;
	}

	async captureToCanvas(
		element: HTMLElement,
		cssW: number,
		cssH: number,
		hideNodes: HTMLElement[] | null = null,
	): Promise<HTMLCanvasElement | null> {
		if (cssW <= 0 || cssH <= 0) return null;
		const hideSet: Set<HTMLElement> | null = hideNodes && hideNodes.length
			? new Set(hideNodes)
			: null;

		try {
			const rendered = await toCanvas(element, {
				width: cssW,
				height: cssH,
				pixelRatio: this.dpr,
				backgroundColor: undefined,
				fontEmbedCSS: this.fontEmbedCSSForElement(element),
				filter: hideSet
					? (node: HTMLElement) => !hideSet.has(node)
					: undefined,
				style: {
					position: 'static',
					top: 'auto',
					left: 'auto',
					right: 'auto',
					bottom: 'auto',
					transform: 'none',
					margin: '0',
				},
			});
			return rendered;
		} catch (err) {
			console.warn('LiquidGlass: captureToCanvas failed for element:', element, err);
			return null;
		}
	}

	invalidateCache(element: HTMLElement): void {
		this.cache.delete(element);
	}

	destroy(): void {
		this.cache.clear();
	}

	private async _captureWithHtmlToImage(
		element: HTMLElement,
		w: number,
		h: number,
		cssW: number,
		cssH: number,
	): Promise<void> {
		if (cssW <= 0 || cssH <= 0 || w <= 0 || h <= 0) return;
		try {
			const rendered = await toCanvas(element, {
				width: cssW,
				height: cssH,
				pixelRatio: this.dpr,
				fontEmbedCSS: this.fontEmbedCSSForElement(element),
			});

			this.cache.set(element, { canvas: rendered, w, h });
			this.onCacheUpdate?.(element);
		} catch (err) {
			console.warn('LiquidGlass: html-to-image capture failed for element:', element, err);
		}
	}
}
