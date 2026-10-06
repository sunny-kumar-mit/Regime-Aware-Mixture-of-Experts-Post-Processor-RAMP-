import { useState, useEffect, useCallback } from 'react';

export type ViewMode = 'desktop' | 'mobile';

const STORAGE_KEY = 'ramp_view_mode';
export const TARGET_DESKTOP_WIDTH = 1280;

/**
 * Detects whether the current device/viewport is a mobile device,
 * touch screen, or small screen (< 1024px width).
 */
export function isMobileOrSmallScreen(): boolean {
  if (typeof window === 'undefined') return false;

  const ua = navigator.userAgent || '';
  const isMobileUA = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua);
  const hasTouch = 'ontouchstart' in window || (navigator.maxTouchPoints && navigator.maxTouchPoints > 0);
  const isNarrowScreen = window.screen && (window.screen.width < 1024 || window.screen.height < 1024);
  const isNarrowWindow = window.innerWidth < 1024;

  return isMobileUA || Boolean(hasTouch && (isNarrowScreen || isNarrowWindow)) || isNarrowWindow;
}

/**
 * Updates the <meta name="viewport"> tag and html classes according to the desired view mode.
 */
export function applyViewport(mode: ViewMode) {
  if (typeof document === 'undefined') return;

  const meta = document.getElementById('ramp-viewport-meta') || document.querySelector('meta[name="viewport"]');
  const html = document.documentElement;

  if (mode === 'desktop') {
    html.classList.add('auto-desktop-view');
    if (meta) {
      const screenW = window.screen && window.screen.width ? window.screen.width : window.innerWidth;
      // Calculate scaling factor to fit 1280px neatly into physical viewport width
      const scale = Math.min(1.0, Math.max(0.2, (screenW > 0 ? screenW : 440) / TARGET_DESKTOP_WIDTH));
      const roundedScale = Math.round(scale * 1000) / 1000;
      meta.setAttribute(
        'content',
        `width=${TARGET_DESKTOP_WIDTH}, initial-scale=${roundedScale}, minimum-scale=0.2, maximum-scale=3.0, user-scalable=yes`
      );
    }
  } else {
    html.classList.remove('auto-desktop-view');
    if (meta) {
      meta.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=3.0, user-scalable=yes');
    }
  }
}

/**
 * Custom hook managing auto desktop view on mobile with persistence and dynamic scaling.
 */
export function useViewMode() {
  const [mode, setMode] = useState<ViewMode>(() => {
    if (typeof window === 'undefined') return 'desktop';
    const saved = localStorage.getItem(STORAGE_KEY) as ViewMode | null;
    if (saved === 'desktop' || saved === 'mobile') return saved;
    // Default requirement: auto-set to desktop view on mobile / small screen
    return 'desktop';
  });

  const [isMobileDevice, setIsMobileDevice] = useState<boolean>(() => isMobileOrSmallScreen());

  // Synchronize viewport and html class on mode change
  useEffect(() => {
    applyViewport(mode);
  }, [mode]);

  // Adjust scale on orientation change or window resize
  useEffect(() => {
    const handleResize = () => {
      const mobileStatus = isMobileOrSmallScreen();
      setIsMobileDevice(mobileStatus);
      if (mode === 'desktop') {
        applyViewport('desktop');
      }
    };

    window.addEventListener('resize', handleResize);
    window.addEventListener('orientationchange', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', handleResize);
    };
  }, [mode]);

  const toggleMode = useCallback(() => {
    setMode((prev) => {
      const next: ViewMode = prev === 'desktop' ? 'mobile' : 'desktop';
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch (e) {
        // Ignore localStorage quota errors
      }
      applyViewport(next);
      return next;
    });
  }, []);

  const setExplicitMode = useCallback((newMode: ViewMode) => {
    setMode(newMode);
    try {
      localStorage.setItem(STORAGE_KEY, newMode);
    } catch (e) {
      // Ignore
    }
    applyViewport(newMode);
  }, []);

  return {
    mode,
    isMobileDevice,
    toggleMode,
    setExplicitMode,
    isDesktopView: mode === 'desktop',
  };
}
