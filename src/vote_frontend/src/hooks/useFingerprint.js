import { useState, useEffect } from 'react';

/**
 * Collect browser fingerprint components.
 * These are used to create a unique device identifier for vote deduplication.
 */
async function collectComponents() {
  const components = {
    // Canvas fingerprint
    canvas: await getCanvasFingerprint(),
    // WebGL fingerprint
    webgl: getWebGLFingerprint(),
    // Hardware info
    hardware: {
      cores: navigator.hardwareConcurrency || 0,
      memory: navigator.deviceMemory || 0,
      platform: navigator.platform || '',
      touchSupport: navigator.maxTouchPoints || 0,
    },
    // Screen info
    screen: {
      width: window.screen.width,
      height: window.screen.height,
      colorDepth: window.screen.colorDepth,
      pixelRatio: window.devicePixelRatio || 1,
    },
    // Timezone
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    // Language
    language: navigator.language,
    // Plugins (limited info)
    plugins: getPluginInfo(),
  };

  return components;
}

/**
 * Generate canvas fingerprint.
 */
async function getCanvasFingerprint() {
  try {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = 200;
    canvas.height = 50;

    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillStyle = '#f60';
    ctx.fillRect(0, 0, 200, 50);
    ctx.fillStyle = '#069';
    ctx.fillText('SplatVote Fingerprint', 2, 15);
    ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
    ctx.fillText('SplatVote Fingerprint', 4, 17);

    return canvas.toDataURL().slice(-50);
  } catch {
    return '';
  }
}

/**
 * Get WebGL fingerprint.
 */
function getWebGLFingerprint() {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (!gl) return '';

    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    if (!debugInfo) return '';

    return {
      vendor: gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL),
      renderer: gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL),
    };
  } catch {
    return '';
  }
}

/**
 * Get plugin info (limited).
 */
function getPluginInfo() {
  try {
    return Array.from(navigator.plugins || [])
      .slice(0, 5)
      .map(p => p.name)
      .join(',');
  } catch {
    return '';
  }
}

/**
 * Hash components using SHA-256.
 */
async function hashComponents(components) {
  const data = JSON.stringify(components);
  const encoder = new TextEncoder();
  const buffer = await crypto.subtle.digest('SHA-256', encoder.encode(data));
  return Array.from(new Uint8Array(buffer))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Custom hook for fingerprint generation.
 * Returns the fingerprint hash or null while loading.
 */
export function useFingerprint() {
  const [fingerprint, setFingerprint] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function generateFingerprint() {
      try {
        // Check for cached fingerprint
        const cached = sessionStorage.getItem('splatvote_fingerprint');
        if (cached && cached.length === 64) {
          setFingerprint(cached);
          setLoading(false);
          return;
        }

        const components = await collectComponents();
        const hash = await hashComponents(components);

        // Cache in session storage
        sessionStorage.setItem('splatvote_fingerprint', hash);

        setFingerprint(hash);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }

    generateFingerprint();
  }, []);

  return { fingerprint, loading, error };
}

export default useFingerprint;
