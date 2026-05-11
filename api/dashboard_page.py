from __future__ import annotations

from api.dashboard_notices import render_category_all_coverage_notice, render_limited_notice
from api.dashboard_page_document import render_dashboard_document
from api.dashboard_page_context import (
    build_progress_context,
    build_save_payload,
    build_stock_meta_filter_context,
    render_industry_options,
    render_status_options,
    render_table_header_html,
    render_topic_options,
    safe_json_script,
    stock_filter_button_text,
)
from api.server_configs import load_server_config_presets


def render_dashboard_page(
    analyzed_stocks,
    candidate_count,
    card_sort,
    cards_data,
    cards_per_row,
    client_render_all_cards,
    compact_progress,
    group_filter,
    industries,
    industry,
    industry_df,
    interval,
    is_limited_analysis,
    limit,
    max_serverless_analysis_stocks,
    page,
    period,
    picker_stocks,
    price_ready_count,
    progress_total_stocks,
    rendered_stock_items,
    rows,
    show_price,
    show_target_price,
    show_volume,
    signal_ready_count,
    sorted_stocks,
    source_stocks,
    status_filter,
    status_filter_values,
    stock_filter_stocks,
    stock_meta_filter_values,
    stock_meta_filters,
    stock_meta_note_filter,
    stock_meta_payload_raw,
    stock_meta_stock_filter,
    stocks,
    subgroup_filter,
    tab,
    total_pages,
    total_stocks,
    valid_groups,
    valid_subgroups,
    watchlist,
) -> str:
    industry_options = render_industry_options(industries=industries, selected_industry=industry)
    status_options = render_status_options(
        selected_status=status_filter,
        status_filter_values=status_filter_values,
    )
    stock_meta_filter_context = build_stock_meta_filter_context(stock_meta_filter_values)
    stock_meta_filter_options = stock_meta_filter_context["options"]
    stock_meta_filter_has_empty = stock_meta_filter_context["has_empty"]
    group_options = render_topic_options(values=valid_groups, selected_value=group_filter, all_label="全部主題")
    subgroup_options = render_topic_options(values=valid_subgroups, selected_value=subgroup_filter, all_label="全部次題材")

    save_payload = build_save_payload(
        tab=tab,
        industry=industry,
        period=period,
        interval=interval,
        limit=limit,
        status_filter=status_filter,
        group_filter=group_filter,
        subgroup_filter=subgroup_filter,
        stock_meta_filters=stock_meta_filters,
        stock_meta_note_filter=stock_meta_note_filter,
        stock_meta_stock_filter=stock_meta_stock_filter,
        stock_meta_payload_raw=stock_meta_payload_raw,
        cards_per_row=cards_per_row,
        watchlist=watchlist,
        show_volume=show_volume,
        show_price=show_price,
        show_target_price=show_target_price,
        card_sort=card_sort,
        compact_progress=compact_progress,
        page=page,
    )
    server_config_presets = load_server_config_presets()
    limited_notice = render_limited_notice(
        candidate_count=candidate_count,
        is_limited_analysis=is_limited_analysis,
        max_serverless_analysis_stocks=max_serverless_analysis_stocks,
    )
    category_all_coverage_notice = render_category_all_coverage_notice(
        tab=tab,
        industry=industry,
        industry_df=industry_df,
        source_stocks=source_stocks,
    )
    progress_context = build_progress_context(
        analyzed_stocks=analyzed_stocks,
        candidate_count=candidate_count,
        is_limited_analysis=is_limited_analysis,
        price_ready_count=price_ready_count,
        progress_total_stocks=progress_total_stocks,
        rendered_stock_items=rendered_stock_items,
        signal_ready_count=signal_ready_count,
        sorted_stocks=sorted_stocks,
        stocks=stocks,
        compact_progress=compact_progress,
    )
    current_progress_stage = progress_context["current_stage"]
    progress_steps_html = progress_context["steps_html"]
    pipeline_progress_json = progress_context["steps_json"]
    progress_panel_class = progress_context["panel_class"]

    table_header_html = render_table_header_html(tab=tab)
    stock_filter_button_label = stock_filter_button_text(stock_meta_stock_filter)
    dashboard_render_items_json = safe_json_script(rendered_stock_items)
    table_header_html_json = safe_json_script(table_header_html)

    body = render_dashboard_document(
        card_sort=card_sort,
        cards_data=cards_data,
        cards_per_row=cards_per_row,
        category_all_coverage_notice=category_all_coverage_notice,
        client_render_all_cards=client_render_all_cards,
        compact_progress=compact_progress,
        current_progress_stage=current_progress_stage,
        dashboard_render_items_json=dashboard_render_items_json,
        group_options=group_options,
        industry_options=industry_options,
        interval=interval,
        limit=limit,
        limited_notice=limited_notice,
        page=page,
        period=period,
        picker_stocks=picker_stocks,
        pipeline_progress_json=pipeline_progress_json,
        progress_panel_class=progress_panel_class,
        progress_steps_html=progress_steps_html,
        rows=rows,
        save_payload=save_payload,
        server_config_presets=server_config_presets,
        show_price=show_price,
        show_target_price=show_target_price,
        show_volume=show_volume,
        status_options=status_options,
        stock_filter_button_label=stock_filter_button_label,
        stock_filter_stocks=stock_filter_stocks,
        stock_meta_filter_has_empty=stock_meta_filter_has_empty,
        stock_meta_filter_options=stock_meta_filter_options,
        stock_meta_filters=stock_meta_filters,
        stock_meta_note_filter=stock_meta_note_filter,
        stock_meta_payload_raw=stock_meta_payload_raw,
        stock_meta_stock_filter=stock_meta_stock_filter,
        subgroup_options=subgroup_options,
        tab=tab,
        table_header_html=table_header_html,
        table_header_html_json=table_header_html_json,
        total_pages=total_pages,
        total_stocks=total_stocks,
        watchlist=watchlist,
    )

    return body
