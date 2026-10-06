"use client";

import React, { useState, useRef, useEffect } from "react";

interface XRayViewerProps {
  imageUrl: string;
  originalFilename?: string;
  overlayHeatmap?: number[][];
  overlayBoxes?: Array<{ x: number; y: number; width: number; height: number; label: string; confidence?: number }>;
  activeFindingLabel?: string;
  onClearOverlay?: () => void;
}

export const XRayViewer: React.FC<XRayViewerProps> = ({
  imageUrl,
  originalFilename = "Chest X-Ray",
  overlayHeatmap,
  overlayBoxes,
  activeFindingLabel,
  onClearOverlay,
}) => {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const [invert, setInvert] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.15 : 0.85;
    setZoom((prev) => Math.min(Math.max(prev * factor, 0.5), 5.0));
  };

  const resetTransform = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setBrightness(100);
    setContrast(100);
    setInvert(false);
  };

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  return (
    <div
      ref={containerRef}
      className={`relative flex flex-col bg-slate-950 border border-slate-800/80 rounded-2xl overflow-hidden shadow-2xl ${
        isFullscreen ? "h-screen w-screen p-4" : "h-[580px] w-full"
      }`}
    >
      {/* Top Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 z-10 text-xs text-slate-300">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-100 truncate max-w-[200px]">{originalFilename}</span>
          {activeFindingLabel && (
            <span className="px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 text-[11px] font-mono">
              Overlay: {activeFindingLabel}
            </span>
          )}
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3">
          {/* Zoom controls */}
          <div className="flex items-center gap-1 bg-slate-800/80 rounded-lg p-1">
            <button
              onClick={() => setZoom((z) => Math.min(z * 1.2, 5))}
              className="p-1.5 hover:bg-slate-700 rounded text-slate-200"
              title="Zoom In"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
            </button>
            <span className="px-1 text-[11px] font-mono">{Math.round(zoom * 100)}%</span>
            <button
              onClick={() => setZoom((z) => Math.max(z * 0.8, 0.5))}
              className="p-1.5 hover:bg-slate-700 rounded text-slate-200"
              title="Zoom Out"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 12H6" />
              </svg>
            </button>
          </div>

          {/* Sliders */}
          <div className="hidden sm:flex items-center gap-2 text-[11px]">
            <label className="flex items-center gap-1">
              <span>Bright:</span>
              <input
                type="range"
                min="50"
                max="180"
                value={brightness}
                onChange={(e) => setBrightness(Number(e.target.value))}
                className="w-16 accent-indigo-500 h-1 bg-slate-700 rounded"
              />
            </label>
            <label className="flex items-center gap-1">
              <span>Contrast:</span>
              <input
                type="range"
                min="50"
                max="200"
                value={contrast}
                onChange={(e) => setContrast(Number(e.target.value))}
                className="w-16 accent-indigo-500 h-1 bg-slate-700 rounded"
              />
            </label>
          </div>

          {/* Invert */}
          <button
            onClick={() => setInvert(!invert)}
            className={`px-2 py-1 rounded text-[11px] font-medium transition ${
              invert ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
            title="Invert Grayscale (Negative view)"
          >
            Invert
          </button>

          {/* Reset */}
          <button
            onClick={resetTransform}
            className="px-2 py-1 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 text-[11px]"
            title="Reset display transformations"
          >
            Reset
          </button>

          {/* Fullscreen */}
          <button
            onClick={toggleFullscreen}
            className="p-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
            title="Toggle Fullscreen"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            </svg>
          </button>

          {onClearOverlay && activeFindingLabel && (
            <button
              onClick={onClearOverlay}
              className="px-2 py-1 rounded bg-rose-950/60 text-rose-300 border border-rose-800 text-[11px] hover:bg-rose-900/60"
            >
              Clear Overlay
            </button>
          )}
        </div>
      </div>

      {/* Main Viewport */}
      <div
        className="relative flex-1 overflow-hidden flex items-center justify-center cursor-grab active:cursor-grabbing select-none"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        <div
          className="relative transition-transform duration-75"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            filter: `brightness(${brightness}%) contrast(${contrast}%) ${invert ? "invert(100%)" : ""}`,
          }}
        >
          {/* Base X-Ray Image */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imageUrl}
            alt={originalFilename}
            className="max-h-[460px] max-w-full object-contain pointer-events-none rounded shadow-lg"
            draggable={false}
          />

          {/* Heatmap Attention Grid Overlay */}
          {overlayHeatmap && (
            <div className="absolute inset-0 grid grid-cols-12 grid-rows-12 pointer-events-none mix-blend-screen opacity-70">
              {overlayHeatmap.flat().map((weight, idx) => (
                <div
                  key={idx}
                  style={{
                    backgroundColor:
                      weight > 0.6
                        ? `rgba(244, 63, 94, ${weight * 0.7})`
                        : weight > 0.3
                        ? `rgba(234, 179, 8, ${weight * 0.5})`
                        : `rgba(99, 102, 241, ${weight * 0.3})`,
                  }}
                  className="w-full h-full transition-colors"
                />
              ))}
            </div>
          )}

          {/* Bounding Box Localization Overlay */}
          {overlayBoxes &&
            overlayBoxes.map((box, bIdx) => (
              <div
                key={bIdx}
                className="absolute border-2 border-indigo-400/90 bg-indigo-500/15 rounded pointer-events-none shadow-lg"
                style={{
                  left: `${box.x * 100}%`,
                  top: `${box.y * 100}%`,
                  width: `${box.width * 100}%`,
                  height: `${box.height * 100}%`,
                }}
              >
                <div className="absolute -top-6 left-0 bg-indigo-900/90 text-indigo-200 text-[10px] font-mono px-1.5 py-0.5 rounded border border-indigo-500/40 whitespace-nowrap">
                  {box.label}
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* Footer Info */}
      <div className="px-4 py-2 bg-slate-900/80 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
        <span>Scroll to zoom · Click & drag to pan</span>
        <span className="font-mono text-slate-500">100% Client-Side Reversible Display</span>
      </div>
    </div>
  );
};
