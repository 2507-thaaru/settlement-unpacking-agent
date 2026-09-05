"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";

type NeuformMode = "dark" | "light";
type NeuformModePreference = NeuformMode | "auto";

export type GatewayFlowProps = {
  mode?: NeuformModePreference;
  speed?: number;
  density?: number;
  strokeWidth?: number;
  opacity?: number;
  className?: string;
  style?: CSSProperties;
};

const DEFAULTS = {
  mode: "auto" as NeuformModePreference,
  speed: 1,
  density: 1,
  strokeWidth: 1,
  opacity: 1,
};

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function readAutomaticMode(): NeuformMode {
  if (typeof document === "undefined") return "dark";
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

function useAutomaticMode(enabled: boolean) {
  const [mode, setMode] = useState<NeuformMode>("dark");

  useEffect(() => {
    if (!enabled || typeof document === "undefined") return;
    const root = document.documentElement;
    const update = () => setMode(readAutomaticMode());
    const observer = new MutationObserver(update);
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });
    update();
    return () => observer.disconnect();
  }, [enabled]);

  return mode;
}

type Particle = {
  x: number;
  y: number;
  t: number;
  speed: number;
  life: number;
  maxLife: number;
};

/**
 * Ambient flow-field canvas. Streams of particles drift along a smooth noise
 * field, leaving soft trails — used behind the live knowledge graph.
 */
export default function GatewayFlow({
  mode = DEFAULTS.mode,
  speed = DEFAULTS.speed,
  density = DEFAULTS.density,
  strokeWidth = DEFAULTS.strokeWidth,
  opacity = DEFAULTS.opacity,
  className,
  style,
}: GatewayFlowProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const automatic = useAutomaticMode(mode === "auto");
  const resolvedMode: NeuformMode = mode === "auto" ? automatic : mode;

  const safeSpeed = clamp(speed, 0, 3);
  const safeDensity = clamp(density, 0.25, 2.5);
  const safeStroke = clamp(strokeWidth, 0.25, 8);
  const safeOpacity = clamp(opacity, 0.05, 1);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let width = 0;
    let height = 0;
    let dpr = 1;
    let particles: Particle[] = [];
    let frame = 0;
    let raf = 0;

    const count = Math.max(14, Math.round(90 * safeDensity));

    const spawn = (): Particle => ({
      x: Math.random() * width,
      y: Math.random() * height,
      t: Math.random() * 1000,
      speed: 0.4 + Math.random() * 1.1,
      life: 0,
      maxLife: 240 + Math.random() * 360,
    });

    const field = (x: number, y: number, t: number) =>
      Math.sin(x * 0.0035 + t * 0.0004) * 1.4 +
      Math.cos(y * 0.0042 - t * 0.0003) * 1.2 +
      Math.sin((x + y) * 0.0018 + t * 0.0002) * 0.9;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      dpr = Math.min(2, window.devicePixelRatio || 1);
      width = Math.max(1, rect.width);
      height = Math.max(1, rect.height);
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      particles = Array.from({ length: count }, spawn);
    };

    const stroke =
      resolvedMode === "light" ? "26, 31, 42" : "255, 255, 255";
    const fade =
      resolvedMode === "light"
        ? "rgba(238, 241, 246, 0.07)"
        : "rgba(8, 10, 18, 0.07)";

    const render = () => {
      frame += 1;
      ctx.fillStyle = fade;
      ctx.fillRect(0, 0, width, height);

      ctx.lineCap = "round";
      for (const p of particles) {
        const angle = field(p.x, p.y, frame + p.t);
        const step = p.speed * safeSpeed * (reduced ? 0 : 1);
        const nx = p.x + Math.cos(angle) * step;
        const ny = p.y + Math.sin(angle) * step;

        const alpha =
          0.32 *
          safeOpacity *
          Math.sin((p.life / p.maxLife) * Math.PI);

        ctx.strokeStyle = `rgba(${stroke}, ${Math.max(0, alpha).toFixed(3)})`;
        ctx.lineWidth = safeStroke * 1.1;
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(nx, ny);
        ctx.stroke();

        p.x = nx;
        p.y = ny;
        p.life += 1;

        if (
          p.life > p.maxLife ||
          p.x < -20 ||
          p.x > width + 20 ||
          p.y < -20 ||
          p.y > height + 20
        ) {
          Object.assign(p, spawn(), { life: 0 });
        }
      }

      raf = window.requestAnimationFrame(render);
    };

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    raf = window.requestAnimationFrame(render);

    return () => {
      window.cancelAnimationFrame(raf);
      observer.disconnect();
    };
  }, [resolvedMode, safeDensity, safeOpacity, safeSpeed, safeStroke]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className={className}
      style={{ display: "block", width: "100%", height: "100%", ...style }}
    />
  );
}
