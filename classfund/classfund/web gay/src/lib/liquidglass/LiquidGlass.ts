/**
 * LiquidGlass — main orchestrator for the liquid glass effect library.
 *
 * Coordinates between:
 *   - HtmlCapture  (captures individual DOM elements into reusable canvases)
 *   - GlassRenderer (WebGL pipeline for the glass effect)
 *
 * Handles child ordering, layered compositing, floating (drag)
 * behaviour, resize, and the render loop.
 *
 * Usage:
 *   import { LiquidGlass } from './LiquidGlass';
 *   LiquidGlass.init({ root, glassElements });
 */

import { DEFAULTS, SHADOW_PAD } from './defaults';
import type { GlassConfig } from './defaults';
import { HtmlCapture } from './HtmlCapture';
import { GlassRenderer } from './GlassRenderer';

/** Options accepted by {@link LiquidGlass.init}. */
export interface LiquidGlassOptions {
	/** Root container element. */
	root: HTMLElement;
	/** Elements to apply the glass effect to. */
	glassElements?: NodeListOf<HTMLElement> | HTMLElement[];
	/** Override the default configuration values. */
	defaults?: Partial<GlassConfig>;
}

interface DragState {
	active: boolean;
	element: HTMLElement | null;
	startX: number;
	startY: number;
	origTx: number;
	origTy: number;
}

interface GlassCacheEntry {
	centerX: number;
	centerY: number;
}

interface ConfigCachedElement extends HTMLElement {
	configCache?: Partial<GlassConfig>;
	configCacheKey?: string;
}

interface SizeEntry {
	w: number;
	h: number;
}

interface ObjectFitRect {
	sx: number;
	sy: number;
	sw: number;
	sh: number;
}

interface SampleRect {
	x: number;
	y: number;
	w: number;
	h: number;
}

const BUTTON_CLASS = 'liquid-glass-button';
const STYLE_ID = 'liquid-glass-button-styles';
const BUTTON_CSS = `
.${BUTTON_CLASS} {
	cursor: pointer;
}
`;

interface ButtonState {
	hover: boolean;
	pressed: boolean;
}

export class LiquidGlass {
	static async init(options: LiquidGlassOptions): Promise<LiquidGlass> {
		const instance = new LiquidGlass(options);
		await instance._start();
		return instance;
	}

	readonly root: HTMLElement;
	readonly defaults: GlassConfig;
	readonly glassSet: Set<HTMLElement>;
	readonly glassCanvases: Map<HTMLElement, HTMLCanvasElement>;
	readonly capture: HtmlCapture;
	readonly renderer: GlassRenderer;

	fps = 0;

	private _running = false;
	private _rafId = 0;
	private _hasDynamic = false;
	private _globalDirty = true;
	private readonly _glassDirty = new Set<HTMLElement>();
	private readonly _userMarkedChanged = new Set<HTMLElement>();
	private _capturingGlassContent = false;
	private readonly _glassContentDirty = new Set<HTMLElement>();
	private _fpsFrames = 0;
	private _fpsTime = 0;

	private _observer: MutationObserver | null = null;
	private _glassSubtreeObserver: MutationObserver | null = null;

	private _sortedChildren: HTMLElement[] = [];
	private readonly _glassCache = new Map<HTMLElement, GlassCacheEntry>();
	private readonly _glassContentImages = new Map<HTMLElement, HTMLCanvasElement>();
	private readonly _glassLastSize = new Map<HTMLElement, SizeEntry>();
	private readonly _buttonStates = new Map<HTMLElement, ButtonState>();
	private readonly _buttonListeners = new Map<HTMLElement, Array<() => void>>();
	private readonly _sceneCanvas: HTMLCanvasElement;
	private readonly _sceneCtx: CanvasRenderingContext2D;

	private readonly _drag: DragState = {
		active: false,
		element: null,
		startX: 0,
		startY: 0,
		origTx: 0,
		origTy: 0,
	};

	private readonly _onResize: () => void;
	private readonly _onPointerDown: (e: PointerEvent) => void;
	private readonly _onPointerMove: (e: PointerEvent) => void;
	private readonly _onPointerUp: (e: PointerEvent) => void;

	constructor({ root, glassElements, defaults = {} }: LiquidGlassOptions) {
		if (!root) throw new Error('LiquidGlass: `root` element is required.');

		this.root = root;
		this.defaults = { ...DEFAULTS, ...defaults };
		this.glassSet = new Set(Array.from(glassElements || []));
		this.glassCanvases = new Map();
		this.capture = new HtmlCapture(root);
		this.capture.onCacheUpdate = (element) => {
			this._markGlassesIntersecting(element);
		};
		this.renderer = new GlassRenderer();
		this._sceneCanvas = document.createElement('canvas');
		this._sceneCtx = this._sceneCanvas.getContext('2d')!;

		this.renderer.canvas.addEventListener('webglcontextrestored', () => {
			this._glassCache.clear();
			this._globalDirty = true;
		});

		this._onResize = this._handleResize.bind(this);
		this._onPointerDown = this._handlePointerDown.bind(this);
		this._onPointerMove = this._handlePointerMove.bind(this);
		this._onPointerUp = this._handlePointerUp.bind(this);
	}

	private async _start(): Promise<void> {
		this.root.style.userSelect = 'none';
		(this.root.style as CSSStyleDeclaration & { webkitUserSelect?: string }).webkitUserSelect = 'none';
		this._setupGlassElements();
		this._hasDynamic = this._detectDynamic();
		this._sortedChildren = this._getSortedChildren();
		this._handleResize();

		await this.capture.prefetchFontEmbedCSS();
		await this._captureGlassContent();
		await this._prewarmStaticCaptures();

		window.addEventListener('resize', this._onResize);
		this.root.addEventListener('pointerdown', this._onPointerDown);
		window.addEventListener('pointermove', this._onPointerMove);
		window.addEventListener('pointerup', this._onPointerUp);

		this._observer = new MutationObserver(() => {
			this._sortedChildren = this._getSortedChildren();
			this._globalDirty = true;
		});
		this._observer.observe(this.root, { childList: true });

		this._glassSubtreeObserver = new MutationObserver((mutations) => {
			for (const mutation of mutations) {
				const owner = this._closestGlassAncestor(mutation.target);
				if (mutation.type === 'attributes' && mutation.attributeName === 'data-config') {
					if (owner) this._markGlassAndDependents(owner);
					continue;
				}
				if (owner) {
					this._glassContentDirty.add(owner);
					this._markGlassAndDependents(owner);
				}
			}
		});
		for (const el of this.glassSet) {
			this._glassSubtreeObserver.observe(el, {
				childList: true,
				subtree: true,
				characterData: true,
				attributes: true,
				attributeFilter: ['data-config'],
			});
		}
		this._glassContentDirty.clear();

		this._running = true;
		this._globalDirty = true;
		this._rafId = requestAnimationFrame(() => this._renderLoop());
	}

	destroy(): void {
		this._running = false;
		cancelAnimationFrame(this._rafId);

		this.root.style.removeProperty('user-select');
		this.root.style.removeProperty('-webkit-user-select');

		window.removeEventListener('resize', this._onResize);
		this.root.removeEventListener('pointerdown', this._onPointerDown);
		window.removeEventListener('pointermove', this._onPointerMove);
		window.removeEventListener('pointerup', this._onPointerUp);

		this._observer?.disconnect();
		this._observer = null;
		this._glassSubtreeObserver?.disconnect();
		this._glassSubtreeObserver = null;

		for (const [el, canvas] of this.glassCanvases) {
			canvas.remove();
			el.style.removeProperty('position');
			el.style.removeProperty('overflow');
			el.style.removeProperty('touch-action');
			el.classList.remove(BUTTON_CLASS);
		}
		this.glassCanvases.clear();
		this._glassCache.clear();
		this._glassContentImages.clear();
		this._glassLastSize.clear();

		for (const removers of this._buttonListeners.values()) {
			for (const r of removers) r();
		}
		this._buttonListeners.clear();
		this._buttonStates.clear();

		document.getElementById(STYLE_ID)?.remove();

		this.capture.destroy();
		this.renderer.destroy();
	}

	private _setupGlassElements(): void {
		let needsButtonStyles = false;

		for (const el of this.glassSet) {
			if (el.parentElement !== this.root) {
				console.warn('LiquidGlass: glass element must be a direct child of root, skipping.', el);
				this.glassSet.delete(el);
				continue;
			}

			const currentPosition = window.getComputedStyle(el).position;
			if (currentPosition === 'static') {
				el.style.position = 'relative';
			}
			el.style.overflow = 'visible';

			const config = this._getConfig(el);

			if (config.floating) {
				el.style.touchAction = 'none';
			}

			if (config.button) {
				el.classList.add(BUTTON_CLASS);
				needsButtonStyles = true;
				this._setupButtonListeners(el);
			}

			const canvas = document.createElement('canvas');
			canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:-1;';
			el.insertBefore(canvas, el.firstChild);

			this.glassCanvases.set(el, canvas);
		}

		if (needsButtonStyles && !document.getElementById(STYLE_ID)) {
			const style = document.createElement('style');
			style.id = STYLE_ID;
			style.textContent = BUTTON_CSS;
			document.head.appendChild(style);
		}
	}

	private _closestGlassAncestor(node: Node): HTMLElement | null {
		let cur: Node | null = node;
		while (cur) {
			if (cur.nodeType === 1 && this.glassSet.has(cur as HTMLElement)) {
				return cur as HTMLElement;
			}
			cur = cur.parentNode;
		}
		return null;
	}

	private _markGlassAndDependents(
		element: HTMLElement,
		rectOverride?: DOMRect,
	): void {
		if (this.glassSet.has(element)) {
			this._glassDirty.add(element);
		}

		const rootRect = this.root.getBoundingClientRect();
		const dpr = window.devicePixelRatio || 1;
		const elementDOMRect = rectOverride ?? element.getBoundingClientRect();
		const elementBox = this._getPixelRect(
			elementDOMRect,
			rootRect,
			dpr,
			this.glassSet.has(element) ? SHADOW_PAD : 0,
		);

		let seenElement = false;
		for (const child of this._sortedChildren) {
			if (child === element) { seenElement = true; continue; }
			if (!seenElement) continue;
			if (!this.glassSet.has(child)) continue;
			const sampleRect = this._getPixelRect(
				child.getBoundingClientRect(), rootRect, dpr, SHADOW_PAD,
			);
			if (LiquidGlass._rectsIntersect(elementBox, sampleRect)) {
				this._glassDirty.add(child);
			}
		}
	}

	private _markGlassesIntersecting(element: HTMLElement): void {
		const rootRect = this.root.getBoundingClientRect();
		const dpr = window.devicePixelRatio || 1;
		const elementBox = this._getPixelRect(
			element.getBoundingClientRect(), rootRect, dpr,
			this.glassSet.has(element) ? SHADOW_PAD : 0,
		);
		for (const glass of this.glassSet) {
			const sampleRect = this._getPixelRect(
				glass.getBoundingClientRect(), rootRect, dpr, SHADOW_PAD,
			);
			if (LiquidGlass._rectsIntersect(elementBox, sampleRect)) {
				this._glassDirty.add(glass);
			}
		}
	}

	markChanged(element?: HTMLElement): void {
		if (!element) {
			this._globalDirty = true;
			return;
		}
		this._userMarkedChanged.add(element);
	}

	private _setupButtonListeners(el: HTMLElement): void {
		const state: ButtonState = { hover: false, pressed: false };
		this._buttonStates.set(el, state);

		const mark = () => this._markGlassAndDependents(el);
		const onOver = () => { state.hover = true; mark(); };
		const onOut = () => { state.hover = false; state.pressed = false; mark(); };
		const onDown = () => { state.pressed = true; mark(); };
		const onUp = () => { state.pressed = false; mark(); };

		el.addEventListener('pointerover', onOver);
		el.addEventListener('pointerout', onOut);
		el.addEventListener('pointerdown', onDown);
		el.addEventListener('pointerup', onUp);
		el.addEventListener('pointercancel', onUp);

		this._buttonListeners.set(el, [
			() => el.removeEventListener('pointerover', onOver),
			() => el.removeEventListener('pointerout', onOut),
			() => el.removeEventListener('pointerdown', onDown),
			() => el.removeEventListener('pointerup', onUp),
			() => el.removeEventListener('pointercancel', onUp),
		]);
	}

	private async _captureGlassContent(
		targets: Set<HTMLElement> | null = null,
	): Promise<void> {
		if (this._capturingGlassContent) return;
		this._capturingGlassContent = true;
		try {
			for (const [el, glassCanvas] of this.glassCanvases) {
				if (targets && !targets.has(el)) continue;
				const rect = el.getBoundingClientRect();
				const img = await this.capture.captureToCanvas(
					el,
					rect.width,
					rect.height,
					[glassCanvas],
				);
				if (img) {
					this._glassContentImages.set(el, img);
				}
			}
		} finally {
			this._capturingGlassContent = false;
		}
	}

	private async _prewarmStaticCaptures(): Promise<void> {
		for (const child of this._sortedChildren) {
			if (this.glassSet.has(child)) continue;
			const tag = child.tagName;
			if (tag === 'CANVAS' || tag === 'IMG' || tag === 'VIDEO') continue;
			if (child.hasAttribute('data-dynamic')) continue;
			try {
				await this.capture.captureElement(child, false);
			} catch (err) {
				console.warn('LiquidGlass: prewarm capture failed:', child, err);
			}
		}
	}

	private _getSortedChildren(): HTMLElement[] {
		const children = Array.from(this.root.children) as HTMLElement[];
		const rootDisplay = window.getComputedStyle(this.root).display;
		const isFlexOrGridParent =
			rootDisplay === 'flex' || rootDisplay === 'inline-flex' ||
			rootDisplay === 'grid' || rootDisplay === 'inline-grid';

		const tagged = children.map((el, domIndex) => {
			const style = window.getComputedStyle(el);
			const hasStackingContext =
				LiquidGlass._formsStackingContext(style, isFlexOrGridParent);
			const rawZ = parseInt(style.zIndex, 10);
			const zIndex = isNaN(rawZ) ? 0 : rawZ;
			return { el, domIndex, hasStackingContext, zIndex };
		});

		tagged.sort((a, b) => {
			if (!a.hasStackingContext && b.hasStackingContext) return -1;
			if (a.hasStackingContext && !b.hasStackingContext) return 1;
			if (a.hasStackingContext && b.hasStackingContext) {
				if (a.zIndex !== b.zIndex) return a.zIndex - b.zIndex;
			}
			return a.domIndex - b.domIndex;
		});

		return tagged.map(t => t.el);
	}

	private static _formsStackingContext(
		style: CSSStyleDeclaration,
		isFlexOrGridParent: boolean,
	): boolean {
		if (style.position !== 'static') return true;
		if (isFlexOrGridParent && style.zIndex !== 'auto') return true;
		if (parseFloat(style.opacity) < 1) return true;
		if (style.transform !== 'none' && style.transform !== '') return true;
		if (style.filter !== 'none' && style.filter !== '') return true;
		if (style.perspective !== 'none' && style.perspective !== '') return true;
		if (style.clipPath !== 'none' && style.clipPath !== '') return true;
		if (style.mixBlendMode !== 'normal' && style.mixBlendMode !== '') return true;
		if (style.isolation === 'isolate') return true;

		const bf = style.backdropFilter
			|| (style as unknown as { webkitBackdropFilter?: string }).webkitBackdropFilter;
		if (bf && bf !== 'none') return true;

		const mask = style.maskImage
			|| (style as unknown as { webkitMaskImage?: string }).webkitMaskImage;
		if (mask && mask !== 'none') return true;

		const contain = style.contain;
		if (contain && /\b(layout|paint|strict|content)\b/.test(contain)) return true;

		if (style.willChange) {
			const triggers = new Set([
				'transform', 'opacity', 'filter', 'backdrop-filter',
				'perspective', 'clip-path', 'mask', 'mask-image',
				'isolation', 'mix-blend-mode',
			]);
			const tokens = style.willChange.split(',').map(t => t.trim());
			for (const t of tokens) {
				if (triggers.has(t)) return true;
			}
		}

		return false;
	}

	private _detectDynamic(): boolean {
		const dynEls = this.root.querySelectorAll('[data-dynamic]');
		for (const el of dynEls) {
			if (!this.glassSet.has(el as HTMLElement)) {
				return true;
			}
		}
		const videos = this.root.querySelectorAll('video');
		for (const vid of videos) {
			if (!this.glassSet.has(vid as unknown as HTMLElement)) {
				return true;
			}
		}
		return false;
	}

	private _getConfig(el: HTMLElement): GlassConfig {
		const cachedEl = el as ConfigCachedElement;
		const configKey = el.dataset.config ?? '';

		if (cachedEl.configCacheKey !== configKey) {
			let perElement: Partial<GlassConfig> = {};
			if (configKey) {
				try {
					const parsed = JSON.parse(configKey);
					if (parsed && typeof parsed === 'object') {
						perElement = parsed as Partial<GlassConfig>;
					} else {
						console.warn('LiquidGlass: data-config must decode to an object for element:', el);
					}
				} catch (_e) {
					console.warn('LiquidGlass: invalid JSON in data-config for element:', el);
				}
			}
			cachedEl.configCache = perElement;
			cachedEl.configCacheKey = configKey;
		}

		const config = { ...this.defaults, ...(cachedEl.configCache || {}) };

		if (config.button) {
			const state = this._buttonStates.get(el);
			if (state) {
				if (state.pressed) {
					config.zRadius = config.zRadius * 0.8;
					config.shadowSpread = config.shadowSpread * 1.2;
				} else if (state.hover) {
					config.brightness = config.brightness + 0.2;
				}
			}
		}

		return config;
	}

	private _handleResize(): void {
		const dpr = window.devicePixelRatio || 1;
		const rect = this.root.getBoundingClientRect();

		this.capture.resize(dpr);
		this.renderer.resize(Math.round(rect.width * dpr), Math.round(rect.height * dpr));

		for (const el of this.glassSet) {
			this._updateGlassCanvasSize(el);
		}

		this._glassCache.clear();
		for (const el of this.glassSet) this._glassContentDirty.add(el);
		this._globalDirty = true;
	}

	private _updateGlassCanvasSize(el: HTMLElement): void {
		const canvas = this.glassCanvases.get(el);
		if (!canvas) return;
		const dpr = window.devicePixelRatio || 1;
		const elW = Math.round(el.offsetWidth);
		const elH = Math.round(el.offsetHeight);
		const padW = SHADOW_PAD * 2;
		const padH = SHADOW_PAD * 2;
		canvas.width = Math.round((elW + padW) * dpr);
		canvas.height = Math.round((elH + padH) * dpr);
		canvas.style.cssText = [
			'position:absolute',
			`left:${-SHADOW_PAD}px`,
			`top:${-SHADOW_PAD}px`,
			`width:${elW + padW}px`,
			`height:${elH + padH}px`,
			'pointer-events:none',
			'z-index:-1'
		].join(';') + ';';
		this._glassLastSize.set(el, { w: elW, h: elH });
	}

	private _checkGlassSizeChanges(): boolean {
		let changed = false;
		for (const el of this.glassSet) {
			const w = el.offsetWidth;
			const h = el.offsetHeight;
			const last = this._glassLastSize.get(el);
			if (!last
				|| Math.abs(last.w - w) > 0.5
				|| Math.abs(last.h - h) > 0.5
			) {
				this._updateGlassCanvasSize(el);
				this._glassCache.delete(el);
				this.capture.invalidateCache(el);
				this._glassContentDirty.add(el);
				changed = true;
			}
		}
		return changed;
	}

	private static _getTranslateXY(el: HTMLElement): [number, number] {
		const style = getComputedStyle(el);
		const matrix = style.transform;
		if (!matrix || matrix === 'none') return [0, 0];
		const m = matrix.match(/matrix\(([^)]+)\)/);
		if (m) {
			const parts = m[1].split(',').map(Number);
			return [parts[4] || 0, parts[5] || 0];
		}
		return [0, 0];
	}

	private _handlePointerDown(e: PointerEvent): void {
		for (let i = this._sortedChildren.length - 1; i >= 0; i--) {
			const el = this._sortedChildren[i];
			if (!this.glassSet.has(el)) continue;

			const config = this._getConfig(el);
			if (!config.floating) continue;

			const rect = el.getBoundingClientRect();
			const elW = el.offsetWidth;
			const elH = el.offsetHeight;
			const visualLeft = rect.left + (rect.width - elW) / 2;
			const visualTop = rect.top + (rect.height - elH) / 2;

			if (
				e.clientX >= visualLeft && e.clientX <= visualLeft + elW &&
				e.clientY >= visualTop && e.clientY <= visualTop + elH
			) {
				const [tx, ty] = LiquidGlass._getTranslateXY(el);
				this._drag.active = true;
				this._drag.element = el;
				this._drag.startX = e.clientX;
				this._drag.startY = e.clientY;
				this._drag.origTx = tx;
				this._drag.origTy = ty;
				el.style.cursor = 'grabbing';
				el.setPointerCapture(e.pointerId);
				e.preventDefault();
				break;
			}
		}
	}

	private _handlePointerMove(e: PointerEvent): void {
		if (!this._drag.active) {
			for (const el of this.glassSet) {
				const config = this._getConfig(el);
				if (!config.floating) continue;
				const rect = el.getBoundingClientRect();
				const elW = el.offsetWidth;
				const elH = el.offsetHeight;
				const visualLeft = rect.left + (rect.width - elW) / 2;
				const visualTop = rect.top + (rect.height - elH) / 2;
				if (
					e.clientX >= visualLeft && e.clientX <= visualLeft + elW &&
					e.clientY >= visualTop && e.clientY <= visualTop + elH
				) {
					el.style.cursor = 'grab';
				} else {
					el.style.cursor = '';
				}
			}
			return;
		}

		const el = this._drag.element!;
		const dx = e.clientX - this._drag.startX;
		const dy = e.clientY - this._drag.startY;
		let newTx = this._drag.origTx + dx;
		let newTy = this._drag.origTy + dy;

		const rootRect = this.root.getBoundingClientRect();
		const elW = el.offsetWidth;
		const elH = el.offsetHeight;
		const elRect = el.getBoundingClientRect();
		const [curTx, curTy] = LiquidGlass._getTranslateXY(el);
		const baseLeft = (elRect.left + (elRect.width - elW) / 2) - rootRect.left - curTx;
		const baseTop = (elRect.top + (elRect.height - elH) / 2) - rootRect.top - curTy;
		const margin = 10;
		const posLeft = baseLeft + newTx;
		const posTop = baseTop + newTy;
		const maxLeft = rootRect.width - elW - margin;
		const maxTop = rootRect.height - elH - margin;
		if (posLeft < margin) newTx += margin - posLeft;
		if (posTop < margin) newTy += margin - posTop;
		if (posLeft > maxLeft) newTx -= posLeft - maxLeft;
		if (posTop > maxTop) newTy -= posTop - maxTop;

		const oldRect = el.getBoundingClientRect();
		this._markGlassAndDependents(el, oldRect);
		el.style.transform = `translate(${newTx}px, ${newTy}px)`;
		this._markGlassAndDependents(el);
	}

	private _handlePointerUp(_e: PointerEvent): void {
		if (!this._drag.active) return;
		const dragged = this._drag.element!;
		dragged.style.cursor = '';
		this._drag.active = false;
		this._drag.element = null;
		this._markGlassAndDependents(dragged);
	}

	private _renderLoop(): void {
		if (!this._running) return;

		const now = performance.now();
		this._fpsFrames++;
		if (now - this._fpsTime >= 1000) {
			this.fps = this._fpsFrames;
			this._fpsFrames = 0;
			this._fpsTime = now;
		}

		if (this._checkGlassSizeChanges()) {
		}

		if (this._glassContentDirty.size > 0 && !this._capturingGlassContent) {
			const targets = new Set(this._glassContentDirty);
			this._glassContentDirty.clear();
			this._captureGlassContent(targets);
		}

		try {
			this._renderFrame();
		} catch (err) {
			console.error('LiquidGlass: render error:', err);
		}

		this._rafId = requestAnimationFrame(() => this._renderLoop());
	}

	private _renderFrame(): void {
		const dpr = window.devicePixelRatio || 1;
		const rootRect = this.root.getBoundingClientRect();
		const isDragging = this._drag.active;

		if (this._userMarkedChanged.size > 0) {
			for (const el of this._userMarkedChanged) {
				this._markGlassesIntersecting(el);
			}
			this._userMarkedChanged.clear();
		}

		if (this._globalDirty) {
			for (const el of this.glassSet) this._glassDirty.add(el);
			this._globalDirty = false;
		}

		const needsRender = this._glassDirty.size > 0
			|| this._hasDynamic
			|| isDragging;
		if (!needsRender) return;

		const dirtyTargets = new Set(this._glassDirty);
		this._glassDirty.clear();

		const renderedThisFrame: Array<{ rect: SampleRect }> = [];

		for (const child of this._sortedChildren) {
			if (!this.glassSet.has(child)) continue;
			this._renderGlassElement(
				child,
				rootRect,
				dpr,
				isDragging,
				dirtyTargets,
				renderedThisFrame,
			);
		}
	}

	private _renderGlassElement(
		child: HTMLElement,
		rootRect: DOMRect,
		dpr: number,
		isDragging: boolean,
		dirtyTargets: Set<HTMLElement>,
		renderedThisFrame: Array<{ rect: SampleRect }>,
	): void {
		const config = this._getConfig(child);
		const elRect = child.getBoundingClientRect();
		const elW = child.offsetWidth;
		const elH = child.offsetHeight;
		const centerX = (elRect.left - rootRect.left) + elRect.width / 2;
		const centerY = (elRect.top - rootRect.top) + elRect.height / 2;
		const glassCanvas = this.glassCanvases.get(child);
		const isBeingDragged = isDragging && this._drag.element === child;
		const sampleRect = this._getPixelRect(elRect, rootRect, dpr, SHADOW_PAD);

		const cached = this._glassCache.get(child);
		const posChanged = !cached
			|| Math.abs(cached.centerX - centerX) > 0.5
			|| Math.abs(cached.centerY - centerY) > 0.5;
		const hasDynamicContributors = this._hasDynamic
			&& this._glassHasDynamicContributors(child, sampleRect, rootRect, dpr);

		let priorGlassChanged = false;
		for (const r of renderedThisFrame) {
			if (LiquidGlass._rectsIntersect(r.rect, sampleRect)) {
				priorGlassChanged = true;
				break;
			}
		}

		const isExplicitlyDirty = dirtyTargets.has(child);

		const needsShaderRender = isDragging
			? (isBeingDragged || isExplicitlyDirty || priorGlassChanged || hasDynamicContributors)
			: (!cached || posChanged || isExplicitlyDirty || priorGlassChanged || hasDynamicContributors);

		if (needsShaderRender && glassCanvas) {
			const renderW = glassCanvas.width;
			const renderH = glassCanvas.height;
			this._composeSceneForGlass(child, sampleRect, rootRect, dpr);
			this.renderer.uploadAndBlur(
				this._sceneCanvas,
				0,
				0,
				renderW,
				renderH,
				config.blurAmount,
			);
			this.renderer.clear();
			this.renderer.renderGlassPanel(
				config,
				elW,
				elH,
				dpr,
			);

			const ctx = glassCanvas.getContext('2d')!;
			ctx.clearRect(0, 0, glassCanvas.width, glassCanvas.height);
			ctx.drawImage(
				this.renderer.canvas,
				0, 0, glassCanvas.width, glassCanvas.height,
				0, 0, glassCanvas.width, glassCanvas.height,
			);

			this._glassCache.set(child, { centerX, centerY });
			renderedThisFrame.push({ rect: sampleRect });
		}
	}

	private _composeSceneForGlass(
		currentGlass: HTMLElement,
		sampleRect: SampleRect,
		rootRect: DOMRect,
		dpr: number,
	): void {
		this._prepareSceneCanvas(sampleRect.w, sampleRect.h);

		for (const child of this._sortedChildren) {
			if (child === currentGlass) break;
			if (this.glassSet.has(child)) {
				this._drawPriorGlassToScene(child, sampleRect, rootRect, dpr);
			} else {
				this._drawNonGlassChildToScene(child, sampleRect, rootRect, dpr);
			}
		}
	}

	private _prepareSceneCanvas(width: number, height: number): void {
		if (this._sceneCanvas.width !== width || this._sceneCanvas.height !== height) {
			this._sceneCanvas.width = width;
			this._sceneCanvas.height = height;
		} else {
			this._sceneCtx.clearRect(0, 0, width, height);
		}
		this._sceneCtx.fillStyle = '#ffffff';
		this._sceneCtx.fillRect(0, 0, width, height);
	}

	private _glassHasDynamicContributors(
		currentGlass: HTMLElement,
		sampleRect: SampleRect,
		rootRect: DOMRect,
		dpr: number,
	): boolean {
		if (this._childHasDynamicContent(currentGlass)) return true;

		for (const child of this._sortedChildren) {
			if (child === currentGlass) break;
			if (this.glassSet.has(child)) continue;
			if (!this._childHasDynamicContent(child)) continue;
			if (this._childTouchesSample(child, sampleRect, rootRect, dpr)) {
				return true;
			}
		}
		return false;
	}

	private _childHasDynamicContent(child: HTMLElement): boolean {
		if (child.hasAttribute('data-dynamic')) return true;
		if (child.tagName === 'VIDEO') return true;
		return child.querySelector('[data-dynamic], video') !== null;
	}

	private _drawNonGlassChildToScene(
		child: HTMLElement,
		sampleRect: SampleRect,
		rootRect: DOMRect,
		dpr: number,
	): void {
		const tag = child.tagName;

		if (tag === 'CANVAS' || tag === 'IMG' || tag === 'VIDEO') {
			this._drawMediaElement(child, this._sceneCtx, sampleRect, rootRect, dpr);
			return;
		}

		if (!this._elementTouchesSample(child, sampleRect, rootRect, dpr)) {
			return;
		}

		this._captureMediaDescendants(child, this._sceneCtx, sampleRect, rootRect, dpr);

		const isDynamic = child.hasAttribute('data-dynamic');
		this.capture.captureElement(child, isDynamic);
		const rect = this._getPixelRect(child.getBoundingClientRect(), rootRect, dpr);
		this.capture.drawCachedElement(
			child,
			this._sceneCtx,
			rect.x - sampleRect.x,
			rect.y - sampleRect.y,
			rect.w,
			rect.h,
		);
	}

	private _captureMediaDescendants(
		parent: HTMLElement,
		targetCtx: CanvasRenderingContext2D,
		sampleRect: SampleRect,
		rootRect: DOMRect,
		dpr: number,
	): void {
		const mediaEls = parent.querySelectorAll('img, video, canvas');
		for (const el of mediaEls) {
			const htmlEl = el as HTMLElement;
			let isGlassCanvas = false;
			for (const [, gc] of this.glassCanvases) {
				if (gc === el) { isGlassCanvas = true; break; }
			}
			if (isGlassCanvas) continue;

			this._drawMediaElement(htmlEl, targetCtx, sampleRect, rootRect, dpr);
		}
	}

	private _drawMediaElement(
		el: HTMLElement,
		targetCtx: CanvasRenderingContext2D,
		sampleRect: SampleRect,
		rootRect: DOMRect,
		dpr: number,
	): boolean {
		const tag = el.tagName;
		const r = el.getBoundingClientRect();
		if (!this._elementTouchesSample(el, sampleRect, rootRect, dpr)) return false;
		const rect = this._getPixelRect(r, rootRect, dpr);
		const dx = rect.x - sampleRect.x;
		const dy = rect.y - sampleRect.y;
		const dw = rect.w;
		const dh = rect.h;

		if (dw <= 0 || dh <= 0) return false;

		if (tag === 'CANVAS') {
			const liveCanvas = el as HTMLCanvasElement;
			if (liveCanvas.width <= 0 || liveCanvas.height <= 0) return false;
			targetCtx.drawImage(liveCanvas, dx, dy, dw, dh);
			return true;
		} else if (tag === 'IMG') {
			const img = el as HTMLImageElement;
			if (!img.complete || img.naturalWidth === 0) return false;
			this._drawMediaFitted(
				targetCtx,
				img,
				img.naturalWidth,
				img.naturalHeight,
				el,
				r,
				dx,
				dy,
				dw,
				dh,
			);
			return true;
		} else if (tag === 'VIDEO') {
			const vid = el as HTMLVideoElement;
			if (vid.readyState < 1) return false;
			try {
				this._drawMediaFitted(
					targetCtx,
					vid,
					vid.videoWidth,
					vid.videoHeight,
					el,
					r,
					dx,
					dy,
					dw,
					dh,
				);
			} catch {
				return false;
			}
			return true;
		}
		return false;
	}

	private _drawMediaFitted(
		targetCtx: CanvasRenderingContext2D,
		mediaEl: HTMLImageElement | HTMLVideoElement,
		natW: number,
		natH: number,
		child: HTMLElement,
		r: DOMRect,
		dx: number,
		dy: number,
		dw: number,
		dh: number,
	): void {
		if (natW && natH) {
			const computed = getComputedStyle(child);
			const fit = computed.objectFit || 'fill';
			const pos = computed.objectPosition || '50% 50%';
			const src = LiquidGlass._objectFitRect(natW, natH, r.width, r.height, fit, pos);
			targetCtx.drawImage(mediaEl, src.sx, src.sy, src.sw, src.sh, dx, dy, dw, dh);
		} else {
			targetCtx.drawImage(mediaEl, dx, dy, dw, dh);
		}
	}

	private _drawPriorGlassToScene(
		child: HTMLElement,
		sampleRect: SampleRect,
		rootRect: DOMRect,
		dpr: number,
	): void {
		const glassCanvas = this.glassCanvases.get(child);
		const elRect = child.getBoundingClientRect();
		if (glassCanvas) {
			const shaderRect = this._getPixelRect(elRect, rootRect, dpr, SHADOW_PAD);
			if (LiquidGlass._rectsIntersect(shaderRect, sampleRect)) {
				this._sceneCtx.drawImage(
					glassCanvas,
					0,
					0,
					glassCanvas.width,
					glassCanvas.height,
					shaderRect.x - sampleRect.x,
					shaderRect.y - sampleRect.y,
					shaderRect.w,
					shaderRect.h,
				);
			}
		}

		const contentImg = this._glassContentImages.get(child);
		if (!contentImg) return;
		const contentRect = this._getPixelRect(elRect, rootRect, dpr);
		if (!LiquidGlass._rectsIntersect(contentRect, sampleRect)) return;
		this._sceneCtx.drawImage(
			contentImg,
			contentRect.x - sampleRect.x,
			contentRect.y - sampleRect.y,
			contentRect.w,
			contentRect.h,
		);
	}

	private _getPixelRect(
		rect: DOMRect,
		rootRect: DOMRect,
		dpr: number,
		pad = 0,
	): SampleRect {
		return {
			x: Math.round((rect.left - rootRect.left - pad) * dpr),
			y: Math.round((rect.top - rootRect.top - pad) * dpr),
			w: Math.round((rect.width + pad * 2) * dpr),
			h: Math.round((rect.height + pad * 2) * dpr),
		};
	}

	private _childTouchesSample(
		child: HTMLElement,
		sampleRect: SampleRect,
		rootRect: DOMRect,
		dpr: number,
	): boolean {
		if (this._elementTouchesSample(child, sampleRect, rootRect, dpr)) return true;

		for (const el of child.querySelectorAll('[data-dynamic], video')) {
			if (this._elementTouchesSample(el as HTMLElement, sampleRect, rootRect, dpr)) {
				return true;
			}
		}
		return false;
	}

	private _elementTouchesSample(
		element: HTMLElement,
		sampleRect: SampleRect,
		rootRect: DOMRect,
		dpr: number,
	): boolean {
		const pad = this._getPaintOverflowPad(element);
		const bounds = this._getPixelRect(element.getBoundingClientRect(), rootRect, dpr, pad);
		return LiquidGlass._rectsIntersect(bounds, sampleRect);
	}

	private _getPaintOverflowPad(element: HTMLElement): number {
		if (this.glassSet.has(element)) return SHADOW_PAD;

		const style = getComputedStyle(element);
		const backdropFilter = style.backdropFilter
			|| (style as CSSStyleDeclaration & { webkitBackdropFilter?: string }).webkitBackdropFilter;
		const maskImage = style.maskImage
			|| (style as CSSStyleDeclaration & { webkitMaskImage?: string }).webkitMaskImage;

		const paintsOutsideBounds =
			(style.boxShadow && style.boxShadow !== 'none')
			|| (style.textShadow && style.textShadow !== 'none')
			|| (style.filter && style.filter !== 'none')
			|| (backdropFilter && backdropFilter !== 'none')
			|| (maskImage && maskImage !== 'none')
			|| (style.mixBlendMode && style.mixBlendMode !== 'normal');

		return paintsOutsideBounds ? SHADOW_PAD : 0;
	}

	private static _rectsIntersect(a: SampleRect, b: SampleRect): boolean {
		return a.x < b.x + b.w
			&& a.x + a.w > b.x
			&& a.y < b.y + b.h
			&& a.y + a.h > b.y;
	}

	static _objectFitRect(
		natW: number,
		natH: number,
		boxW: number,
		boxH: number,
		fit: string,
		pos: string,
	): ObjectFitRect {
		let sx = 0, sy = 0, sw = natW, sh = natH;

		if (fit === 'fill' || (fit === 'scale-down' && natW <= boxW && natH <= boxH)) {
			return { sx, sy, sw, sh };
		}

		const parts = pos.split(/\s+/);
		const parseFrac = (v: string, total: number): number => {
			if (v.endsWith('%')) return parseFloat(v) / 100;
			return parseFloat(v) / total;
		};
		const fx = parseFrac(parts[0] || '50%', boxW);
		const fy = parseFrac(parts[1] || '50%', boxH);

		if (fit === 'cover') {
			const scale = Math.max(boxW / natW, boxH / natH);
			sw = boxW / scale;
			sh = boxH / scale;
			sx = (natW - sw) * fx;
			sy = (natH - sh) * fy;
		} else if (fit === 'contain' || fit === 'scale-down') {
			return { sx: 0, sy: 0, sw: natW, sh: natH };
		} else if (fit === 'none') {
			sw = boxW;
			sh = boxH;
			sx = (natW - sw) * fx;
			sy = (natH - sh) * fy;
		}

		sx = Math.max(0, Math.min(sx, natW - 1));
		sy = Math.max(0, Math.min(sy, natH - 1));
		sw = Math.min(sw, natW - sx);
		sh = Math.min(sh, natH - sy);

		return { sx, sy, sw, sh };
	}
}
