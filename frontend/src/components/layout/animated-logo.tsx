"use client";

import { motion, useAnimationControls } from "motion/react";
import { cn } from "@/lib/utils";
import { useEffect, useId, useMemo } from "react";

export interface AnimatedLogoProps {
  appName: string;
  className?: string;
}

export function AnimatedLogo({ appName, className }: AnimatedLogoProps) {
  const uid = useId().replace(/:/g, "");
  const gradId = `logo-grad-${uid}`;

  // Controls for sequencing entrance
  const swooshControls = useAnimationControls();
  const ribbonControls = useAnimationControls();
  const svgGroupControls = useAnimationControls();

  // Split app name into individual characters for staggered reveal
  const letters = useMemo(() => appName.split(""), [appName]);

  useEffect(() => {
    async function runEntrance() {
      // Phase 1: SVG group scales + rotates into place (spring)
      svgGroupControls.start({
        scale: 1,
        rotate: 0,
        opacity: 1,
        transition: {
          type: "spring",
          stiffness: 120,
          damping: 14,
          mass: 0.8,
          delay: 0.1,
        },
      });

      // Phase 2: Stroke draw-in for swoosh
      await swooshControls.start({
        pathLength: 1,
        strokeOpacity: 0.7,
        transition: {
          pathLength: { duration: 1.2, ease: [0.65, 0, 0.35, 1] },
          strokeOpacity: { duration: 0.3 },
        },
      });

      // Phase 2b: Swoosh fill fades in after stroke completes
      swooshControls.start({
        fillOpacity: 1,
        strokeOpacity: 0,
        transition: {
          fillOpacity: { duration: 0.6, ease: "easeOut" },
          strokeOpacity: { duration: 0.8 },
        },
      });
    }

    async function runRibbon() {
      // Start 0.4s after mount — stroke draws while swoosh is animating
      await new Promise((r) => setTimeout(r, 400));

      await ribbonControls.start({
        pathLength: 1,
        strokeOpacity: 0.5,
        transition: {
          pathLength: { duration: 1.0, ease: [0.65, 0, 0.35, 1] },
          strokeOpacity: { duration: 0.2 },
        },
      });

      // Ribbon fill — snappy but not instant
      ribbonControls.start({
        fillOpacity: 1,
        strokeOpacity: 0,
        transition: {
          fillOpacity: { duration: 0.25, ease: "easeOut" },
          strokeOpacity: { duration: 0.4 },
        },
      });
    }

    runEntrance();
    runRibbon();
  }, [
    swooshControls,
    ribbonControls,
    svgGroupControls,
  ]);

  return (
    <div
      className={cn("relative z-10 flex items-center gap-2.5", className)}
    >
      <motion.svg
        viewBox="0 0 104 85.8"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="relative h-6 w-auto"
        initial={{ scale: 0.75, rotate: -8, opacity: 0 }}
        animate={svgGroupControls}
      >
        <defs>
          {/* Original gradient for the swoosh fill */}
          <linearGradient
            id={gradId}
            x1="85.89"
            y1="29.27"
            x2="4.43"
            y2="86.31"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0" stopColor="#fff" stopOpacity="0.4" />
            <stop offset="1" stopColor="#fff" />
          </linearGradient>

        </defs>

        {/* Bottom-left swoosh: stroke draws in first, then fill appears */}
        <motion.path
          d="M59.6,70.28c5.58-.27,10.59-3.5,13.11-8.46l8.4-16.54,7.04-12.77c-27.93,5.6-56.65-.07-68.81,21.31-4.38,7.7-15.28,31.98-15.28,31.98,8.55-9.4,14.62-14.12,26.35-14.12l29.19-1.39Z"
          fill={`url(#${gradId})`}
          fillRule="evenodd"
          stroke="rgba(255,255,255,0.8)"
          strokeWidth="1"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{
            pathLength: 0,
            fillOpacity: 0,
            strokeOpacity: 0,
          }}
          animate={swooshControls}
        />

        {/* Top ribbon: draws with delay, overlapping the swoosh */}
        <motion.path
          d="M54.05,42.38c19.02,0,36.26,2.63,40.66-5.71.24-.45.39-.94.51-1.43L104,0C84.01,9.04,37.27,3.08,17.52,9.17c-5.06,1.56-8.93,5.65-10.3,10.75L1.95,39.58c-1.81,6.75-6.41,19.28,10.64,25.44,0,0-6.48-5.36-3.24-14.17,1.42-3.55,4.17-5.83,6.93-7.03,4.2-1.82,8.6-1.53,11.67-1.43,6.52.21,26.1,0,26.1,0Z"
          fill="white"
          fillRule="evenodd"
          stroke="rgba(255,255,255,0.6)"
          strokeWidth="1"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{
            pathLength: 0,
            fillOpacity: 0,
            strokeOpacity: 0,
          }}
          animate={ribbonControls}
        />

      </motion.svg>

      {/* App name text: letter-by-letter reveal with spring overshoot */}
      <span
        className="relative text-xl font-bold tracking-tight text-white/90"
        style={{ fontFamily: "var(--font-cabinet), sans-serif" }}
        aria-label={appName}
      >
        {letters.map((letter, i) => (
          <motion.span
            key={`${letter}-${i}`}
            className="inline-block"
            initial={{ opacity: 0, y: 12, filter: "blur(4px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{
              type: "spring",
              stiffness: 200,
              damping: 16,
              mass: 0.6,
              delay: 1.3 + i * 0.06,
            }}
            style={letter === " " ? { width: "0.25em" } : undefined}
          >
            {letter === " " ? "\u00A0" : letter}
          </motion.span>
        ))}
      </span>
    </div>
  );
}

export default AnimatedLogo;
