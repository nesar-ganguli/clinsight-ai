{% macro stable_bigint_id(value_expression) -%}
    (('x' || substr(md5({{ value_expression }}::text), 1, 15))::bit(60)::bigint)
{%- endmacro %}
