"""Web routes for the relationship analysis application."""

import json
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..adapters.testdata import TestDataAdapter
from ..adapters.weflow import WeFlowAdapter
from ..engine.frequency import analyze_frequency
from ..engine.reciprocity import analyze_reciprocity
from ..models import Sender

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
IMPORTS_DIR = BASE_DIR / "data" / "imports"


def _fmt_seconds(s: float) -> str:
    """Format seconds into a human-readable string."""
    if s <= 0:
        return "-"
    if s < 60:
        return f"{s:.0f}秒"
    if s < 3600:
        return f"{s / 60:.0f}分"
    return f"{s / 3600:.1f}时"


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    storage = request.app.state.storage
    contacts = storage.list_contacts()

    rows = ""
    for c in contacts:
        conv = storage.get_conversation_by_contact(c.id)
        msg_count = conv.message_count if conv else 0
        last_active = ""
        if conv and conv.last_msg_time:
            last_active = conv.last_msg_time.strftime("%Y-%m-%d %H:%M")

        rows += f"""
        <tr>
            <td><a href="/contact/{c.id}">{c.name}</a></td>
            <td>{c.platform}</td>
            <td>{msg_count}</td>
            <td>{last_active}</td>
        </tr>"""

    if not rows:
        rows = '<tr><td colspan="4">暂无联系人，请先导入数据。</td></tr>'

    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>Friend Relationship Analysis</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }}
            table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
            th, td {{ text-align: left; padding: 0.75rem; border-bottom: 1px solid #e0e0e0; }}
            th {{ background: #f5f5f5; }}
            a {{ color: #2563eb; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .import-btn {{ display: inline-block; padding: 0.5rem 1.5rem; background: #2563eb; color: white; border-radius: 4px; margin: 1rem 0; }}
            .import-btn:hover {{ background: #1d4ed8; text-decoration: none; }}
        </style>
    </head>
    <body>
        <h1>👥 Friend Relationship Analysis</h1>
        <p><a href="/import" class="import-btn">导入聊天数据</a> | <a href="/dashboard">对比面板 →</a></p>
        <table>
            <thead>
                <tr><th>联系人</th><th>平台</th><th>消息数</th><th>最近活跃</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </body>
    </html>
    """


@router.get("/import", response_class=HTMLResponse)
def import_page(request: Request):
    """Show available import files and trigger import."""
    storage = request.app.state.storage
    files = sorted(IMPORTS_DIR.glob("*.json")) if IMPORTS_DIR.exists() else []
    adapter = TestDataAdapter()

    results = []
    for fp in files:
        try:
            # Auto-detect format: WeFlow JSON has a "weflow" top-level key
            with open(fp, "r", encoding="utf-8") as fh:
                peek = json.load(fh)
            if "weflow" in peek:
                adapter: Adapter = WeFlowAdapter()
            else:
                adapter = TestDataAdapter()

            contacts, messages, platform = adapter.parse(str(fp))
            for contact in contacts:
                c = storage.get_or_create_contact(contact.name, contact.platform)
                conv = storage.get_or_create_conversation(c.id)
                for m in messages:
                    m.conversation_id = conv.id
                inserted = storage.bulk_insert_messages(messages)
                storage.update_conversation_stats(conv.id)
                results.append((fp.name, "成功", f"{len(messages)} 条消息"))
        except Exception as e:
            results.append((fp.name, "失败", str(e)))

    result_html = ""
    for name, status, detail in results:
        result_html += f'<tr><td>{name}</td><td style="color: {"green" if status == "成功" else "red"}">{status}</td><td>{detail}</td></tr>'

    if not result_html:
        result_html = '<tr><td colspan="3">未找到导入文件，请将 JSON 文件放入 data/imports/ 目录。</td></tr>'

    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>导入 - Friend Analysis</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }}
            table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
            th, td {{ text-align: left; padding: 0.75rem; border-bottom: 1px solid #e0e0e0; }}
            th {{ background: #f5f5f5; }}
            a {{ color: #2563eb; }}
        </style>
    </head>
    <body>
        <h1>📥 导入聊天数据</h1>
        <table>
            <thead><tr><th>文件</th><th>状态</th><th>详情</th></tr></thead>
            <tbody>{result_html}</tbody>
        </table>
        <p><a href="/">← 返回联系人列表</a></p>
    </body>
    </html>
    """


@router.get("/contact/{contact_id}", response_class=HTMLResponse)
def contact_detail(contact_id: int, request: Request):
    """Detail page showing frequency + reciprocity metrics for a single contact."""
    storage = request.app.state.storage
    contact = storage.get_contact(contact_id)
    if not contact:
        return HTMLResponse("<h1>联系人未找到</h1>", status_code=404)

    conv = storage.get_conversation_by_contact(contact_id)
    messages = storage.get_messages(conv.id) if conv else []
    freq = analyze_frequency(conv, messages) if conv else None
    recip = analyze_reciprocity(conv, messages) if conv else None

    if not conv or not freq or not recip:
        return f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head><meta charset="UTF-8"><title>{contact.name}</title></head>
        <body style="font-family: sans-serif; max-width: 800px; margin: 2rem auto;">
            <h1>{contact.name}</h1>
            <p>暂无对话数据，请先导入消息。</p>
            <p><a href="/">← 返回联系人列表</a></p>
        </body>
        </html>
        """

    # ── monthly trend rows ────────────────────────────────
    trend_rows = ""
    max_count = max((m["count"] for m in freq.monthly_trend), default=1) or 1
    for m in freq.monthly_trend:
        pct = m["count"] / max_count * 100 if max_count > 0 else 0
        bar = f'<div style="width:{pct}%;height:16px;background:#2563eb;border-radius:3px;min-width:2px" title="{m["count"]} messages"></div>'
        trend_rows += f"<tr><td>{m['label']}</td><td>{m['count']}</td><td style='width:60%'>{bar}</td></tr>"

    # ── silent period rows ────────────────────────────────
    silent_rows = ""
    if freq.silent_periods:
        for sp in freq.silent_periods:
            silent_rows += f"<tr><td>{sp['start']}</td><td>{sp['end']}</td><td>{sp['days']}天</td></tr>"
    else:
        silent_rows = '<tr><td colspan="3" style="color:green">无沉默期——联系一直很稳定！</td></tr>'

    # Direction: who is "driving" the conversation more
    if recip.me_initiation_rate > 0.55:
        init_verdict = "你发起了大部分对话。"
    elif recip.contact_initiation_rate > 0.55:
        init_verdict = f"{contact.name}发起了大部分对话。"
    else:
        init_verdict = "双方发起对话的次数相当。"

    if recip.me_reply_avg_seconds > 0 and recip.contact_reply_avg_seconds > 0:
        if recip.me_reply_avg_seconds < recip.contact_reply_avg_seconds * 0.7:
            reply_verdict = "你回复明显更快。"
        elif recip.contact_reply_avg_seconds < recip.me_reply_avg_seconds * 0.7:
            reply_verdict = f"{contact.name}回复明显更快。"
        else:
            reply_verdict = "双方回复速度相当。"
    else:
        reply_verdict = ""

    if recip.me_avg_length > recip.contact_avg_length * 1.5:
        length_verdict = "你发的消息更长。"
    elif recip.contact_avg_length > recip.me_avg_length * 1.5:
        length_verdict = f"{contact.name}发的消息更长。"
    else:
        length_verdict = "双方消息长度接近。"

    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>{contact.name} - Friend Analysis</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1.5rem; color: #1a1a1a; }}
            h1 {{ margin-bottom: 0.25rem; }}
            .subtitle {{ color: #666; margin-bottom: 2rem; }}
            h2 {{ border-bottom: 2px solid #e5e7eb; padding-bottom: 0.25rem; margin-top: 2rem; }}
            .kpi {{ display: flex; gap: 2rem; flex-wrap: wrap; margin: 1.5rem 0; }}
            .kpi-item {{ background: #f9fafb; border-radius: 8px; padding: 1rem 1.5rem; min-width: 140px; }}
            .kpi-label {{ font-size: 0.85rem; color: #6b7280; }}
            .kpi-value {{ font-size: 1.75rem; font-weight: 700; color: #111827; }}
            .verdict {{ background: #eff6ff; border-left: 4px solid #2563eb; padding: 0.75rem 1rem; margin: 1rem 0; border-radius: 0 4px 4px 0; font-size: 0.95rem; }}
            table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
            th, td {{ text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid #e5e7eb; }}
            th {{ background: #f9fafb; font-weight: 600; font-size: 0.85rem; color: #6b7280; }}
            a {{ color: #2563eb; }}
        </style>
    </head>
    <body>
        <h1>{contact.name}</h1>
        <p class="subtitle">平台：{contact.platform}</p>

        <h2>📊 互动频率</h2>
        <div class="kpi">
            <div class="kpi-item">
                <div class="kpi-label">消息总数</div>
                <div class="kpi-value">{freq.total_count}</div>
            </div>
            <div class="kpi-item">
                <div class="kpi-label">时间跨度</div>
                <div class="kpi-value">{freq.time_span_days}天</div>
            </div>
            <div class="kpi-item">
                <div class="kpi-label">日均消息</div>
                <div class="kpi-value">{freq.daily_avg}</div>
            </div>
        </div>

        <h2>📈 月度趋势</h2>
        <table>
            <thead><tr><th>月份</th><th>消息数</th><th>占比</th></tr></thead>
            <tbody>{trend_rows}</tbody>
        </table>

        <h2>🔇 沉默期（间隔 &gt; 7天）</h2>
        <table>
            <thead><tr><th>开始</th><th>结束</th><th>持续</th></tr></thead>
            <tbody>{silent_rows}</tbody>
        </table>

        <h2>⚖️ 对话均衡度</h2>
        <div class="kpi">
            <div class="kpi-item">
                <div class="kpi-label">你发起</div>
                <div class="kpi-value">{recip.me_initiation_rate * 100:.0f}%</div>
            </div>
            <div class="kpi-item">
                <div class="kpi-label">你回复速度</div>
                <div class="kpi-value">{_fmt_seconds(recip.me_reply_avg_seconds)}</div>
            </div>
            <div class="kpi-item">
                <div class="kpi-label">你消息长度</div>
                <div class="kpi-value">{recip.me_avg_length:.0f}字</div>
            </div>
            <div class="kpi-item">
                <div class="kpi-label">你结束</div>
                <div class="kpi-value">{recip.me_closure_rate * 100:.0f}%</div>
            </div>
        </div>
        <div class="kpi">
            <div class="kpi-item">
                <div class="kpi-label">{contact.name}发起</div>
                <div class="kpi-value">{recip.contact_initiation_rate * 100:.0f}%</div>
            </div>
            <div class="kpi-item">
                <div class="kpi-label">{contact.name}回复速度</div>
                <div class="kpi-value">{_fmt_seconds(recip.contact_reply_avg_seconds)}</div>
            </div>
            <div class="kpi-item">
                <div class="kpi-label">{contact.name}消息长度</div>
                <div class="kpi-value">{recip.contact_avg_length:.0f}字</div>
            </div>
            <div class="kpi-item">
                <div class="kpi-label">{contact.name}结束</div>
                <div class="kpi-value">{recip.contact_closure_rate * 100:.0f}%</div>
            </div>
        </div>
        <div class="verdict">{init_verdict} {reply_verdict} {length_verdict}</div>

        <p style="margin-top:2rem"><a href="/">← 返回联系人列表</a> | <a href="/dashboard">对比面板 →</a></p>
    </body>
    </html>
    """


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    """Comparison dashboard with charts for all contacts."""
    storage = request.app.state.storage
    contacts = storage.list_contacts()

    # Build data for each contact that has messages
    rows: list[dict] = []
    all_trends: dict[str, dict[str, int]] = {}  # contact_name -> {month_label: count}

    for contact in contacts:
        conv = storage.get_conversation_by_contact(contact.id)
        if not conv:
            continue
        messages = storage.get_messages(conv.id)
        if not messages:
            continue
        freq = analyze_frequency(conv, messages)
        recip = analyze_reciprocity(conv, messages)

        rows.append({
            "id": contact.id,
            "name": contact.name,
            "total": freq.total_count,
            "span_days": freq.time_span_days,
            "daily_avg": freq.daily_avg,
            "me_start_pct": recip.me_initiation_rate * 100,
            "me_reply": recip.me_reply_avg_seconds,
            "contact_reply": recip.contact_reply_avg_seconds,
        })

        trend_map: dict[str, int] = {}
        for m in freq.monthly_trend:
            trend_map[m["label"]] = m["count"]
        all_trends[contact.name] = trend_map

    # ── line chart data ───────────────────────────────────
    # Collect all month labels across all contacts
    all_months: list[str] = []
    for trend_map in all_trends.values():
        for month in trend_map:
            if month not in all_months:
                all_months.append(month)
    all_months.sort()

    series_data = []
    for name, trend_map in all_trends.items():
        values = [trend_map.get(month, 0) for month in all_months]
        series_data.append({"name": name, "data": values})

    chart_data = {
        "months": all_months,
        "series": series_data,
        "barLabels": [r["name"] for r in rows],
        "barValues": [r["total"] for r in rows],
    }
    chart_json = json.dumps(chart_data)

    # ── ranking table rows ────────────────────────────────
    table_rows = ""
    for i, r in enumerate(rows, 1):
        table_rows += f"""
        <tr>
            <td>{i}</td>
            <td><a href="/contact/{r['id']}">{r['name']}</a></td>
            <td>{r['total']}</td>
            <td>{r['span_days']}天</td>
            <td>{r['daily_avg']}</td>
            <td>{r['me_start_pct']:.0f}%</td>
            <td>{_fmt_seconds(r['contact_reply'])} / {_fmt_seconds(r['me_reply'])}</td>
        </tr>"""

    no_data_msg = ""
    if not rows:
        no_data_msg = '<p style="color:#666; margin:2rem 0">暂无数据，请先导入聊天数据。</p>'

    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>Dashboard - Friend Analysis</title>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1.5rem; color: #1a1a1a; }}
            h1 {{ margin-bottom: 0.5rem; }}
            h2 {{ border-bottom: 2px solid #e5e7eb; padding-bottom: 0.25rem; margin-top: 2rem; }}
            .chart {{ width: 100%; height: 400px; margin: 1rem 0; }}
            table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
            th, td {{ text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid #e5e7eb; }}
            th {{ background: #f9fafb; font-weight: 600; font-size: 0.85rem; color: #6b7280; }}
            a {{ color: #2563eb; }}
        </style>
    </head>
    <body>
        <h1>📊 对比面板</h1>
        <p><a href="/">← 返回联系人列表</a></p>
        {no_data_msg}

        <h2>📈 月度趋势对比</h2>
        <div id="trend-chart" class="chart"></div>

        <h2>📊 消息总数对比</h2>
        <div id="bar-chart" class="chart"></div>

        <h2>📋 排名</h2>
        <table>
            <thead><tr><th>排名</th><th>联系人</th><th>总数</th><th>跨度</th><th>日均</th><th>你发起</th><th>回复（对方/你）</th></tr></thead>
            <tbody>{table_rows}</tbody>
        </table>

        <script>
            var data = {chart_json};
            var colors = ['#2563eb', '#dc2626', '#16a34a', '#ca8a04', '#9333ea', '#0891b2'];

            // Line chart: monthly trends
            var trendChart = echarts.init(document.getElementById('trend-chart'));
            trendChart.setOption({{
                tooltip: {{ trigger: 'axis' }},
                legend: {{ data: data.series.map(function(s) {{ return s.name; }}) }},
                xAxis: {{ type: 'category', data: data.months }},
                yAxis: {{ type: 'value', name: '消息数' }},
                series: data.series.map(function(s, i) {{
                    return {{
                        name: s.name,
                        type: 'line',
                        data: s.data,
                        smooth: true,
                        lineStyle: {{ color: colors[i % colors.length] }},
                        itemStyle: {{ color: colors[i % colors.length] }}
                    }};
                }})
            }});

            // Bar chart: message counts
            var barChart = echarts.init(document.getElementById('bar-chart'));
            barChart.setOption({{
                tooltip: {{ trigger: 'axis' }},
                xAxis: {{ type: 'category', data: data.barLabels }},
                yAxis: {{ type: 'value', name: '消息总数' }},
                series: [{{
                    type: 'bar',
                    data: data.barValues.map(function(v, i) {{
                        return {{ value: v, itemStyle: {{ color: colors[i % colors.length] }} }};
                    }})
                }}]
            }});
        </script>
    </body>
    </html>
    """
