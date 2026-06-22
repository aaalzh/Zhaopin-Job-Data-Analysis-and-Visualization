import { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import { BarChart, EffectScatterChart, LineChart, PieChart } from "echarts/charts";
import {
  GeoComponent,
  GraphicComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  BarChart,
  EffectScatterChart,
  LineChart,
  PieChart,
  GeoComponent,
  GraphicComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  VisualMapComponent,
  CanvasRenderer,
]);

export function Chart({ option, className = "", ariaLabel }) {
  const elementRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!elementRef.current) return undefined;
    chartRef.current = echarts.init(elementRef.current, null, { renderer: "canvas" });
    const observer = new ResizeObserver(() => chartRef.current?.resize());
    observer.observe(elementRef.current);
    return () => {
      observer.disconnect();
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (chartRef.current && option) {
      chartRef.current.setOption(option, { notMerge: true, lazyUpdate: true });
    }
  }, [option]);

  return <div ref={elementRef} className={`chart ${className}`} role="img" aria-label={ariaLabel} />;
}

export { echarts };
