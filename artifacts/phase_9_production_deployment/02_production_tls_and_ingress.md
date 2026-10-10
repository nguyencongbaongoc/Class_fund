# Production Edge Ingress, CA-Signed TLS & Network Security

## Overview
Edge ingress for `CLASS_FUND_WEB` is secured by a high-performance reverse proxy (Caddy 2.8 with Nginx 1.27 fallback) that terminates external TLS, enforces strict security transport policies, routes API and real-time WebSocket traffic, and insulates internal database and broker infrastructure from direct internet exposure.

## 1. Automated ACME Certificate Lifecycle
The edge proxy is configured for automated CA-signed TLS via Let's Encrypt / ZeroSSL with automatic local fallback:

```caddy
{
    email {$ACME_EMAIL:admin@classfund.local}
    admin off
}

{$DOMAIN:localhost} {
    encode zstd gzip

    # TLS Configuration
    # Uses Let's Encrypt / ZeroSSL when DOMAIN is a valid FQDN;
    # falls back to internal self-signed CA in local/staging environments.
    tls {$ACME_EMAIL:internal}

    # Security Headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
        Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ws: wss:; font-src 'self';"
        Permissions-Policy "camera=(), microphone=(), geolocation=()"
        -Server
    }

    # API and Metrics Routing
    handle /api/* {
        reverse_proxy backend:8000 {
            header_up X-Forwarded-Proto https
            header_up Host {host}
        }
    }

    handle /metrics {
        reverse_proxy backend:8000
    }

    # Real-Time WebSocket Streaming (WSS)
    handle /ws/* {
        reverse_proxy backend:8000 {
            header_up Upgrade {>Upgrade}
            header_up Connection "Upgrade"
            header_up Host {host}
        }
    }

    # Frontend Single Page Application
    handle {
        reverse_proxy frontend:80
    }
}
```

## 2. Hardened Security Transport Policies
1. **HTTP Strict Transport Security (HSTS)**:
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
   - Forces browsers to refuse any plaintext HTTP connections for a minimum of 1 year.
2. **Content Security Policy (CSP)**:
   - Restricts resource loads to origin (`'self'`), allows safe base64 image data for receipt OCR reviews, and permits explicit WebSocket connections (`connect-src 'self' ws: wss:`).
3. **Clickjacking & MIME Protection**:
   - `X-Frame-Options: DENY` prevents framing inside malicious iframes.
   - `X-Content-Type-Options: nosniff` prohibits MIME type sniffing.
4. **Information Disclosure Prevention**:
   - Strips `Server` header to prevent scanner fingerprinting.

## 3. Network Isolation & Service Protection
In `docker-compose.prod.yml`, the network topology is split into:
- **`edge_net` (Public Facing)**: Proxy container binds host ports `80` and `443`.
- **`backend_net` (Internal Bridge)**: Backend, Frontend, and Worker communicate privately.
- **`data_net` (Isolated Bridge)**: MySQL Primary, MySQL Replica, and Redis are attached strictly to internal networks without exposed host ports in production (`ports` directive removed; only internal DNS resolution on `3306`, `3308`, and `6379`).

Database connections utilize `mysql+pymysql` with `ssl_mode=REQUIRED` support enabled in `app/db/session.py` and `app/core/config.py`, ensuring all data-in-transit between backend containers and database nodes is encrypted.
