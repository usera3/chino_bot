/* eslint-disable no-shadow */
/* eslint-disable no-underscore-dangle */
/* eslint-disable @typescript-eslint/ban-ts-comment */
import { memo, useRef, useEffect, useState } from "react";
import { useLive2DConfig } from "@/context/live2d-config-context";
import { useIpcHandlers } from "@/hooks/utils/use-ipc-handlers";
import { useInterrupt } from "@/hooks/utils/use-interrupt";
import { useAudioTask } from "@/hooks/utils/use-audio-task";
import { useLive2DModel } from "@/hooks/canvas/use-live2d-model";
import { useLive2DResize } from "@/hooks/canvas/use-live2d-resize";
import { useAiState, AiStateEnum } from "@/context/ai-state-context";
import { useLive2DExpression } from "@/hooks/canvas/use-live2d-expression";
import { useForceIgnoreMouse } from "@/hooks/utils/use-force-ignore-mouse";
import { useMode } from "@/context/mode-context";

interface Live2DProps {
  showSidebar?: boolean;
}

export const Live2D = memo(
  ({ showSidebar }: Live2DProps): JSX.Element => {
    const { forceIgnoreMouse } = useForceIgnoreMouse();
    const { modelInfo } = useLive2DConfig();
    const { mode } = useMode();
    const internalContainerRef = useRef<HTMLDivElement>(null);
    const { aiState } = useAiState();
    const { resetExpression } = useLive2DExpression();
    const isPet = mode === 'pet';
    const [fallbackAction, setFallbackAction] = useState<{
      preset: string;
      token: string;
    }>({
      preset: 'idle-soft',
      token: 'boot',
    });

    // Get canvasRef from useLive2DResize
    const { canvasRef } = useLive2DResize({
      containerRef: internalContainerRef,
      modelInfo,
      showSidebar,
    });

    // Pass canvasRef to useLive2DModel
    const { isDragging, handlers } = useLive2DModel({
      modelInfo,
      canvasRef,
    });

    // Setup hooks
    useIpcHandlers();
    useInterrupt();
    useAudioTask();

    // Reset expression to default when AI state becomes idle
    useEffect(() => {
      if (aiState === AiStateEnum.IDLE) {
        const lappAdapter = (window as any).getLAppAdapter?.();
        if (lappAdapter) {
          resetExpression(lappAdapter, modelInfo);
        }
      }
    }, [aiState, modelInfo, resetExpression]);

    useEffect(() => {
      const handler = (event: Event) => {
        const detail = (event as CustomEvent).detail as {
          preset?: string;
          token?: string;
        };
        setFallbackAction({
          preset: detail?.preset || 'still-attentive',
          token: detail?.token || `${Date.now()}-${Math.random()}`,
        });
      };
      window.addEventListener('openclaw-companion-action', handler);
      return () => window.removeEventListener('openclaw-companion-action', handler);
    }, []);

    // Expose setExpression for console testing
    // useEffect(() => {
    //   const testSetExpression = (expressionValue: string | number) => {
    //     const lappAdapter = (window as any).getLAppAdapter?.();
    //     if (lappAdapter) {
    //       setExpression(expressionValue, lappAdapter, `[Console Test] Set expression to: ${expressionValue}`);
    //     } else {
    //       console.error('[Console Test] LAppAdapter not found.');
    //     }
    //   };

    //   // Expose the function to the window object
    //   (window as any).testSetExpression = testSetExpression;
    //   console.log('[Debug] testSetExpression function exposed to window.');

    //   // Cleanup function to remove the function from window when the component unmounts
    //   return () => {
    //     delete (window as any).testSetExpression;
    //     console.log('[Debug] testSetExpression function removed from window.');
    //   };
    // }, [setExpression]);

    const handlePointerDown = (e: React.PointerEvent) => {
      handlers.onMouseDown(e);
    };

    const handleContextMenu = (e: React.MouseEvent) => {
      if (!isPet) {
        return;
      }

      e.preventDefault();
      console.log(
        "[ContextMenu] (Pet Mode) Right-click detected, requesting menu...",
      );
      window.api?.showContextMenu?.();
    };

    const fallbackAnimationKey = [
      modelInfo?.fallbackImageUrl ?? '',
      modelInfo?.url ?? '',
      modelInfo?.defaultEmotion ?? '',
      modelInfo?.initialXshift ?? '',
      modelInfo?.initialYshift ?? '',
      modelInfo?.fallbackTopPercent ?? '',
      modelInfo?.fallbackLeft ?? '',
      modelInfo?.fallbackHeight ?? '',
      modelInfo?.scrollToResize ?? '',
      modelInfo?.pointerInteractive ?? '',
      fallbackAction.token,
    ].join(':');

    const fallbackAnimationName = (() => {
      const preset = fallbackAction.preset;
      switch (preset) {
        case 'gentle-nod':
          return 'openclaw-pet-nod';
        case 'wave-soft':
          return 'openclaw-pet-wave';
        case 'lean-in-soft':
          return 'openclaw-pet-lean';
        case 'guarded-soft':
          return 'openclaw-pet-guard';
        case 'slow-blink':
          return 'openclaw-pet-sleepy';
        case 'wake-soft':
          return 'openclaw-pet-wake';
        case 'still-attentive':
          return 'openclaw-pet-attentive';
        case 'idle-soft':
        default:
          return 'openclaw-pet-idle';
      }
    })();

    const fallbackAnimationDuration = (() => {
      switch (fallbackAnimationName) {
        case 'openclaw-pet-wave':
          return '1.15s';
        case 'openclaw-pet-nod':
          return '0.65s';
        case 'openclaw-pet-lean':
          return '0.7s';
        case 'openclaw-pet-guard':
          return '0.7s';
        case 'openclaw-pet-wake':
          return '0.8s';
        case 'openclaw-pet-sleepy':
          return '1.8s';
        case 'openclaw-pet-attentive':
          return '1.2s';
        default:
          return '2.8s';
      }
    })();

    return (
      <div
        ref={internalContainerRef} // Ref for useLive2DResize if it observes this element
        id="live2d-internal-wrapper"
        style={{
          width: isPet ? "220px" : "100%",
          height: isPet ? "320px" : "100%",
          pointerEvents: isPet && forceIgnoreMouse ? "none" : "auto",
          overflow: "hidden",
          position: "absolute",
          left: isPet ? "0px" : undefined,
          top: isPet ? "50%" : undefined,
          transform: isPet ? "translateY(-50%)" : undefined,
          cursor: isDragging ? "grabbing" : "default",
        }}
        onPointerDown={handlePointerDown}
        onContextMenu={handleContextMenu}
        {...handlers}
      >
        <style>{`
          @keyframes openclaw-pet-idle {
            0% { transform: translateY(-50%) translateY(0px); }
            50% { transform: translateY(-50%) translateY(-3px); }
            100% { transform: translateY(-50%) translateY(0px); }
          }
          @keyframes openclaw-pet-nod {
            0% { transform: translateY(-50%) rotate(0deg); }
            35% { transform: translateY(-50%) rotate(7deg) translateY(6px); }
            70% { transform: translateY(-50%) rotate(-2deg) translateY(-1px); }
            100% { transform: translateY(-50%) rotate(0deg); }
          }
          @keyframes openclaw-pet-wave {
            0% { transform: translateY(-50%) rotate(0deg) translateX(0px); }
            20% { transform: translateY(-50%) rotate(4deg) translateX(2px); }
            40% { transform: translateY(-50%) rotate(-6deg) translateX(-1px); }
            60% { transform: translateY(-50%) rotate(5deg) translateX(2px); }
            80% { transform: translateY(-50%) rotate(-4deg) translateX(-1px); }
            100% { transform: translateY(-50%) rotate(0deg) translateX(0px); }
          }
          @keyframes openclaw-pet-lean {
            0% { transform: translateY(-50%) translateX(0px) scale(1); }
            50% { transform: translateY(-50%) translateX(10px) scale(1.03); }
            100% { transform: translateY(-50%) translateX(0px) scale(1); }
          }
          @keyframes openclaw-pet-guard {
            0% { transform: translateY(-50%) translateX(0px); }
            35% { transform: translateY(-50%) translateX(-6px); }
            70% { transform: translateY(-50%) translateX(2px); }
            100% { transform: translateY(-50%) translateX(0px); }
          }
          @keyframes openclaw-pet-sleepy {
            0% { transform: translateY(-50%) translateY(0px) scaleY(1); }
            50% { transform: translateY(-50%) translateY(4px) scaleY(0.98); }
            100% { transform: translateY(-50%) translateY(0px) scaleY(1); }
          }
          @keyframes openclaw-pet-wake {
            0% { transform: translateY(-50%) scale(0.96); }
            40% { transform: translateY(-50%) scale(1.05); }
            100% { transform: translateY(-50%) scale(1); }
          }
          @keyframes openclaw-pet-attentive {
            0% { transform: translateY(-50%) translateY(0px); }
            50% { transform: translateY(-50%) translateY(-2px); }
            100% { transform: translateY(-50%) translateY(0px); }
          }
        `}</style>
        {isPet && modelInfo?.fallbackImageUrl && (
          <img
            key={fallbackAnimationKey}
            src={modelInfo.fallbackImageUrl}
            alt="companion-fallback-body"
            style={{
              position: "absolute",
              left: `${modelInfo.fallbackLeft ?? 24}px`,
              ...(modelInfo.fallbackTopPercent !== undefined
                ? {
                    top: `${modelInfo.fallbackTopPercent}%`,
                    transform: "translateY(-50%)",
                  }
                : {
                    bottom: `${modelInfo.fallbackBottom ?? 72}px`,
                  }),
              height: `${modelInfo.fallbackHeight ?? 140}px`,
              width: "auto",
              pointerEvents: "none",
              userSelect: "none",
              opacity: 0.96,
              filter: "drop-shadow(0 10px 18px rgba(0,0,0,0.18))",
              zIndex: 1,
              transformOrigin: "50% 78%",
              animationName: fallbackAnimationName,
              animationDuration: fallbackAnimationDuration,
              animationTimingFunction: "ease-in-out",
              animationIterationCount:
                fallbackAnimationName === 'openclaw-pet-idle' ||
                fallbackAnimationName === 'openclaw-pet-attentive' ||
                fallbackAnimationName === 'openclaw-pet-sleepy'
                  ? 'infinite'
                  : '1',
            }}
          />
        )}
        <canvas
          id="canvas"
          ref={canvasRef}
          style={{
            width: "100%",
            height: "100%",
            pointerEvents: isPet && forceIgnoreMouse ? "none" : "auto",
            display: "block",
            cursor: isDragging ? "grabbing" : "default",
            position: "relative",
            zIndex: 2,
          }}
        />
      </div>
    );
  },
);

Live2D.displayName = "Live2D";

export { useInterrupt, useAudioTask };
