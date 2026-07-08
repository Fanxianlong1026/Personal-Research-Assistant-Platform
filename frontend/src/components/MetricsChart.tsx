/**
 * 实验指标对比图（ECharts）
 * 以「运行」为横轴，每个指标一组柱/线，直观对比各次运行的指标差异。
 */
import { useEffect, useRef, useState } from 'react';
import { Segmented } from 'antd';
import * as echarts from 'echarts';

interface Props {
  compareData: any;
}

export default function MetricsChart({ compareData }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const [chartType, setChartType] = useState<'bar' | 'line'>('bar');

  useEffect(() => {
    if (!ref.current) return;
    if (!chartRef.current) chartRef.current = echarts.init(ref.current);
    const chart = chartRef.current;

    const rows = compareData?.rows || [];
    const metricKeys: string[] = compareData?.metric_keys || [];
    const categories = rows.map((r: any) => r.variant || `Run ${r.run_number}`);

    const series = metricKeys.map((key) => ({
      name: key,
      type: chartType,
      smooth: chartType === 'line',
      data: rows.map((r: any) => {
        const v = parseFloat(r.metrics?.[key]);
        return Number.isNaN(v) ? null : v;
      }),
    }));

    chart.setOption(
      {
        tooltip: { trigger: 'axis', axisPointer: { type: chartType === 'bar' ? 'shadow' : 'line' } },
        legend: { data: metricKeys, top: 0 },
        grid: { left: 48, right: 24, top: 40, bottom: 70 },
        xAxis: {
          type: 'category',
          data: categories,
          axisLabel: { rotate: categories.length > 4 ? 30 : 0, interval: 0 },
        },
        yAxis: { type: 'value', scale: true },
        series,
      },
      true,
    );
    chart.resize();
  }, [compareData, chartType]);

  useEffect(() => {
    const onResize = () => chartRef.current?.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <Segmented
          size="small"
          value={chartType}
          onChange={(v) => setChartType(v as 'bar' | 'line')}
          options={[
            { label: '柱状图', value: 'bar' },
            { label: '折线图', value: 'line' },
          ]}
        />
      </div>
      <div ref={ref} style={{ width: '100%', height: 320 }} />
    </div>
  );
}
