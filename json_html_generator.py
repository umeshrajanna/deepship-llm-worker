#!/usr/bin/env python3
"""
HTML App Generator - Single File Implementation
LLM generates structure with SVG components for charts
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import anthropic
import os
from datetime import datetime


# ============================================================================
# BASE CSS - MINIMAL RESET ONLY
# ============================================================================

BASE_CSS = """
/* Minimal Reset */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  line-height: 1.6;
}

/* Default table styles */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}

th, td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

th {
  background-color: #f7fafc;
  font-weight: 600;
  color: #2d3748;
}

tr:hover {
  background-color: #f7fafc;
}

/* SVG responsive */
svg {
  max-width: 100%;
  height: auto;
}
"""


# ============================================================================
# SCHEMA SPECIFICATION - WITH SVG COMPONENTS
# ============================================================================

SCHEMA_SPEC = {
    "schemaVersion": "1.0",
    "components": {
        # LAYOUT COMPONENTS
        "container": {
            "tag": "div",
            "description": "Main wrapper container",
            "canHaveChildren": True,
            "allowedAttributes": ["id"]
        },
        "flex": {
            "tag": "div",
            "description": "Flexbox layout container",
            "canHaveChildren": True,
            "allowedAttributes": ["id"]
        },
        "section": {
            "tag": "section",
            "description": "Semantic section element",
            "canHaveChildren": True,
            "allowedAttributes": ["id"]
        },
        
        # CONTENT COMPONENTS
        "heading": {
            "tag": "h1",
            "description": "Heading element (h1-h6)",
            "requiredProps": ["level"],
            "allowedProps": {
                "level": ["h1", "h2", "h3", "h4", "h5", "h6"]
            },
            "canHaveChildren": False,
            "hasTextContent": True,
            "allowedAttributes": ["id"]
        },
        "text": {
            "tag": "p",
            "description": "Paragraph text",
            "canHaveChildren": False,
            "hasTextContent": True,
            "allowedAttributes": ["id"]
        },
        "button": {
            "tag": "button",
            "description": "Button element",
            "canHaveChildren": False,
            "hasTextContent": True,
            "allowedAttributes": ["id", "type", "disabled"]
        },
        "link": {
            "tag": "a",
            "description": "Anchor link",
            "requiredAttributes": ["href"],
            "canHaveChildren": False,
            "hasTextContent": True,
            "allowedAttributes": ["href", "target", "rel", "id"]
        },
        "image": {
            "tag": "img",
            "description": "Image element",
            "requiredAttributes": ["src", "alt"],
            "canHaveChildren": False,
            "selfClosing": True,
            "allowedAttributes": ["src", "alt", "width", "height", "id"]
        },
        "card": {
            "tag": "div",
            "description": "Card container component",
            "canHaveChildren": True,
            "allowedAttributes": ["id"]
        },
        "list": {
            "tag": "ul",
            "description": "List container (ul/ol)",
            "allowedProps": {
                "ordered": [True, False]
            },
            "canHaveChildren": True,
            "allowedAttributes": ["id"]
        },
        "list-item": {
            "tag": "li",
            "description": "List item",
            "canHaveChildren": True,
            "allowedAttributes": ["id"]
        },
        "div": {
            "tag": "div",
            "description": "Generic container div",
            "canHaveChildren": True,
            "allowedAttributes": ["id"]
        },
        "span": {
            "tag": "span",
            "description": "Inline text container",
            "canHaveChildren": True,
            "hasTextContent": True,
            "allowedAttributes": ["id"]
        },
        
        # DATA COMPONENT
        "data-table": {
            "tag": "div",
            "description": "Data table component (renders from data property)",
            "canHaveChildren": False,
            "special": "table",
            "allowedAttributes": ["id"]
        },
        
        # SVG COMPONENTS
        "svg": {
            "tag": "svg",
            "description": "SVG container for charts and graphics",
            "canHaveChildren": True,
            "allowedAttributes": ["viewBox", "width", "height", "xmlns", "id"]
        },
        "rect": {
            "tag": "rect",
            "description": "SVG rectangle (for bar charts)",
            "canHaveChildren": False,
            "selfClosing": True,
            "allowedAttributes": ["x", "y", "width", "height", "fill", "stroke", "stroke-width", "rx", "ry", "opacity", "id"]
        },
        "circle": {
            "tag": "circle",
            "description": "SVG circle (for pie charts, scatter plots)",
            "canHaveChildren": False,
            "selfClosing": True,
            "allowedAttributes": ["cx", "cy", "r", "fill", "stroke", "stroke-width", "opacity", "id"]
        },
        "ellipse": {
            "tag": "ellipse",
            "description": "SVG ellipse",
            "canHaveChildren": False,
            "selfClosing": True,
            "allowedAttributes": ["cx", "cy", "rx", "ry", "fill", "stroke", "stroke-width", "opacity", "id"]
        },
        "line": {
            "tag": "line",
            "description": "SVG line",
            "canHaveChildren": False,
            "selfClosing": True,
            "allowedAttributes": ["x1", "y1", "x2", "y2", "stroke", "stroke-width", "opacity", "id"]
        },
        "polyline": {
            "tag": "polyline",
            "description": "SVG polyline for line charts",
            "canHaveChildren": False,
            "selfClosing": True,
            "allowedAttributes": ["points", "fill", "stroke", "stroke-width", "opacity", "stroke-dasharray", "id"]
        },
        "polygon": {
            "tag": "polygon",
            "description": "SVG polygon",
            "canHaveChildren": False,
            "selfClosing": True,
            "allowedAttributes": ["points", "fill", "stroke", "stroke-width", "opacity", "id"]
        },
        "path": {
            "tag": "path",
            "description": "SVG path for complex shapes (pie slices, curves)",
            "canHaveChildren": False,
            "selfClosing": True,
            "allowedAttributes": ["d", "fill", "stroke", "stroke-width", "opacity", "id"]
        },
        "svg-text": {
            "tag": "text",
            "description": "SVG text element for labels",
            "canHaveChildren": False,
            "hasTextContent": True,
            "allowedAttributes": ["x", "y", "font-size", "font-weight", "font-family", "fill", "text-anchor", "dominant-baseline", "transform", "id"]
        },
        "g": {
            "tag": "g",
            "description": "SVG group element",
            "canHaveChildren": True,
            "allowedAttributes": ["transform", "opacity", "id"]
        }
    },
    
    "customStylesAllowed": True,
    "customStylesRequired": True
}


# ============================================================================
# INITIAL JSON TEMPLATE
# ============================================================================

INITIAL_JSON_TEMPLATE = {
    "schemaVersion": "1.0",
    "structure": {
        "component": "container",
        "classes": ["app-wrapper"],
        "children": [
            {
                "component": "section",
                "classes": ["navbar"],
                "children": [
                    {
                        "component": "div",
                        "classes": ["nav-container"],
                        "children": [
                            {
                                "component": "heading",
                                "props": {"level": "h1"},
                                "classes": ["nav-logo"],
                                "text": "YourBrand"
                            },
                            {
                                "component": "flex",
                                "classes": ["nav-menu"],
                                "children": [
                                    {
                                        "component": "button",
                                        "classes": ["nav-link", "active"],
                                        "text": "Home"
                                    },
                                    {
                                        "component": "button",
                                        "classes": ["nav-link"],
                                        "text": "About"
                                    },
                                    {
                                        "component": "button",
                                        "classes": ["nav-link"],
                                        "text": "Services"
                                    },
                                    {
                                        "component": "button",
                                        "classes": ["nav-link"],
                                        "text": "Portfolio"
                                    },
                                    {
                                        "component": "button",
                                        "classes": ["nav-link"],
                                        "text": "Contact"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "component": "section",
                "classes": ["tabs-section"],
                "children": [
                    {
                        "component": "div",
                        "classes": ["tabs-container"],
                        "children": [
                            {
                                "component": "flex",
                                "classes": ["tab-buttons"],
                                "children": [
                                    {
                                        "component": "button",
                                        "classes": ["tab-btn", "tab-active"],
                                        "text": "🏠 Home"
                                    },
                                    {
                                        "component": "button",
                                        "classes": ["tab-btn"],
                                        "text": "👤 About"
                                    },
                                    {
                                        "component": "button",
                                        "classes": ["tab-btn"],
                                        "text": "⚙️ Services"
                                    },
                                    {
                                        "component": "button",
                                        "classes": ["tab-btn"],
                                        "text": "💼 Portfolio"
                                    },
                                    {
                                        "component": "button",
                                        "classes": ["tab-btn"],
                                        "text": "📧 Contact"
                                    }
                                ]
                            },
                            {
                                "component": "div",
                                "classes": ["tab-content"],
                                "children": [
                                    {
                                        "component": "section",
                                        "classes": ["hero-section"],
                                        "children": [
                                            {
                                                "component": "heading",
                                                "props": {"level": "h1"},
                                                "classes": ["hero-title"],
                                                "text": "Welcome to Your Application"
                                            },
                                            {
                                                "component": "text",
                                                "classes": ["hero-subtitle"],
                                                "text": "Build amazing things with our platform"
                                            },
                                            {
                                                "component": "flex",
                                                "classes": ["hero-buttons"],
                                                "children": [
                                                    {
                                                        "component": "button",
                                                        "classes": ["hero-btn", "btn-primary"],
                                                        "text": "Get Started"
                                                    },
                                                    {
                                                        "component": "button",
                                                        "classes": ["hero-btn", "btn-secondary"],
                                                        "text": "Learn More"
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "component": "section",
                "classes": ["features-section"],
                "children": [
                    {
                        "component": "heading",
                        "props": {"level": "h2"},
                        "classes": ["section-title"],
                        "text": "Key Features"
                    },
                    {
                        "component": "flex",
                        "classes": ["features-grid"],
                        "children": [
                            {
                                "component": "card",
                                "classes": ["feature-card"],
                                "children": [
                                    {
                                        "component": "span",
                                        "classes": ["feature-icon"],
                                        "text": "⚡"
                                    },
                                    {
                                        "component": "heading",
                                        "props": {"level": "h3"},
                                        "classes": ["feature-title"],
                                        "text": "Fast Performance"
                                    },
                                    {
                                        "component": "text",
                                        "classes": ["feature-description"],
                                        "text": "Lightning-fast load times and smooth interactions"
                                    }
                                ]
                            },
                            {
                                "component": "card",
                                "classes": ["feature-card"],
                                "children": [
                                    {
                                        "component": "span",
                                        "classes": ["feature-icon"],
                                        "text": "🎨"
                                    },
                                    {
                                        "component": "heading",
                                        "props": {"level": "h3"},
                                        "classes": ["feature-title"],
                                        "text": "Beautiful Design"
                                    },
                                    {
                                        "component": "text",
                                        "classes": ["feature-description"],
                                        "text": "Modern, elegant interface that users love"
                                    }
                                ]
                            },
                            {
                                "component": "card",
                                "classes": ["feature-card"],
                                "children": [
                                    {
                                        "component": "span",
                                        "classes": ["feature-icon"],
                                        "text": "🔒"
                                    },
                                    {
                                        "component": "heading",
                                        "props": {"level": "h3"},
                                        "classes": ["feature-title"],
                                        "text": "Secure & Reliable"
                                    },
                                    {
                                        "component": "text",
                                        "classes": ["feature-description"],
                                        "text": "Enterprise-grade security you can trust"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    },
    "customStyles": {
        "app-wrapper": {
            "min-height": "100vh",
            "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
        },
        "navbar": {
            "background": "rgba(255, 255, 255, 0.95)",
            "backdrop-filter": "blur(10px)",
            "box-shadow": "0 2px 20px rgba(0, 0, 0, 0.1)",
            "position": "sticky",
            "top": "0",
            "z-index": "1000"
        },
        "nav-container": {
            "max-width": "1200px",
            "margin": "0 auto",
            "padding": "1rem 2rem",
            "display": "flex",
            "justify-content": "space-between",
            "align-items": "center"
        },
        "nav-logo": {
            "font-size": "1.5rem",
            "font-weight": "700",
            "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            "background-clip": "text",
            "-webkit-background-clip": "text",
            "-webkit-text-fill-color": "transparent",
            "margin": "0"
        },
        "nav-menu": {
            "display": "flex",
            "gap": "0.5rem"
        },
        "nav-link": {
            "background": "transparent",
            "border": "none",
            "color": "#4a5568",
            "font-size": "1rem",
            "font-weight": "500",
            "padding": "0.5rem 1rem",
            "cursor": "pointer",
            "transition": "all 0.3s ease",
            "border-radius": "0.5rem"
        },
        "nav-link:hover": {
            "background": "rgba(102, 126, 234, 0.1)",
            "color": "#667eea",
            "transform": "translateY(-2px)"
        },
        "nav-link.active": {
            "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            "color": "white"
        },
        "tabs-section": {
            "max-width": "1200px",
            "margin": "2rem auto",
            "padding": "0 2rem"
        },
        "tabs-container": {
            "background": "white",
            "border-radius": "1rem",
            "box-shadow": "0 10px 40px rgba(0, 0, 0, 0.1)",
            "overflow": "hidden"
        },
        "tab-buttons": {
            "display": "flex",
            "background": "#f7fafc",
            "border-bottom": "2px solid #e2e8f0",
            "gap": "0"
        },
        "tab-btn": {
            "flex": "1",
            "background": "transparent",
            "border": "none",
            "padding": "1rem",
            "font-size": "1rem",
            "font-weight": "500",
            "color": "#4a5568",
            "cursor": "pointer",
            "transition": "all 0.3s ease",
            "border-bottom": "3px solid transparent",
            "position": "relative"
        },
        "tab-btn:hover": {
            "background": "rgba(102, 126, 234, 0.05)",
            "color": "#667eea"
        },
        "tab-btn.tab-active": {
            "color": "#667eea",
            "background": "white",
            "border-bottom-color": "#667eea"
        },
        "tab-content": {
            "padding": "2rem",
            "min-height": "400px"
        },
        "hero-section": {
            "text-align": "center",
            "padding": "3rem 0"
        },
        "hero-title": {
            "font-size": "3rem",
            "font-weight": "800",
            "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            "background-clip": "text",
            "-webkit-background-clip": "text",
            "-webkit-text-fill-color": "transparent",
            "margin-bottom": "1rem",
            "animation": "fadeInUp 0.6s ease"
        },
        "hero-subtitle": {
            "font-size": "1.25rem",
            "color": "#718096",
            "margin-bottom": "2rem",
            "animation": "fadeInUp 0.6s ease 0.2s both"
        },
        "hero-buttons": {
            "display": "flex",
            "gap": "1rem",
            "justify-content": "center",
            "animation": "fadeInUp 0.6s ease 0.4s both"
        },
        "hero-btn": {
            "padding": "0.875rem 2rem",
            "font-size": "1rem",
            "font-weight": "600",
            "border": "none",
            "border-radius": "0.5rem",
            "cursor": "pointer",
            "transition": "all 0.3s ease"
        },
        "btn-primary": {
            "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            "color": "white",
            "box-shadow": "0 4px 15px rgba(102, 126, 234, 0.4)"
        },
        "btn-primary:hover": {
            "transform": "translateY(-2px)",
            "box-shadow": "0 6px 20px rgba(102, 126, 234, 0.5)"
        },
        "btn-secondary": {
            "background": "white",
            "color": "#667eea",
            "border": "2px solid #667eea"
        },
        "btn-secondary:hover": {
            "background": "#667eea",
            "color": "white",
            "transform": "translateY(-2px)"
        },
        "features-section": {
            "max-width": "1200px",
            "margin": "4rem auto",
            "padding": "0 2rem"
        },
        "section-title": {
            "text-align": "center",
            "font-size": "2.5rem",
            "font-weight": "700",
            "color": "white",
            "margin-bottom": "3rem"
        },
        "features-grid": {
            "display": "flex",
            "gap": "2rem",
            "flex-wrap": "wrap",
            "justify-content": "center"
        },
        "feature-card": {
            "background": "white",
            "border-radius": "1rem",
            "padding": "2rem",
            "flex": "1",
            "min-width": "280px",
            "max-width": "350px",
            "text-align": "center",
            "transition": "all 0.3s ease",
            "cursor": "pointer",
            "box-shadow": "0 4px 15px rgba(0, 0, 0, 0.1)"
        },
        "feature-card:hover": {
            "transform": "translateY(-10px)",
            "box-shadow": "0 10px 30px rgba(0, 0, 0, 0.2)"
        },
        "feature-icon": {
            "font-size": "3rem",
            "display": "block",
            "margin-bottom": "1rem"
        },
        "feature-title": {
            "font-size": "1.5rem",
            "font-weight": "600",
            "color": "#2d3748",
            "margin-bottom": "0.5rem"
        },
        "feature-description": {
            "color": "#718096",
            "line-height": "1.6"
        },
        "@keyframes fadeInUp": {
            "from": {
                "opacity": "0",
                "transform": "translateY(30px)"
            },
            "to": {
                "opacity": "1",
                "transform": "translateY(0)"
            }
        }
    }
}


# ============================================================================
# LLM SYSTEM PROMPT
# ============================================================================

def get_system_prompt() -> str:
    return f"""You are an HTML structure generator. You generate clean semantic HTML with custom CSS styling.

COMPONENTS AVAILABLE:
{json.dumps(SCHEMA_SPEC['components'], indent=2)}

HOW TO GENERATE:
1. Use semantic component names from the list above
2. Create custom CSS classes for ALL styling needs
3. Define all classes in the "customStyles" object
4. Use semantic class names (e.g., "weather-card", "temperature-display", "hero-section")

YOU MUST GENERATE ALL STYLES. There are NO pre-defined utility classes.

SVG COMPONENTS FOR CHARTS AND VISUALIZATIONS:
You can create charts and graphics using SVG elements:
- svg: Container (use viewBox="0 0 600 400" for responsive sizing)
- rect: Rectangles (for bar charts)
- circle: Circles (for pie charts, scatter plots)
- line: Lines (for axes, connectors)
- polyline: Multi-point lines (for line charts)
- path: Complex shapes (for pie slices using arc commands)
- svg-text: Text labels and annotations
- g: Group elements together

EXAMPLE BAR CHART:
{{
  "component": "svg",
  "classes": ["bar-chart"],
  "attributes": {{"viewBox": "0 0 600 400"}},
  "children": [
    {{
      "component": "rect",
      "classes": ["bar"],
      "attributes": {{"x": "50", "y": "200", "width": "40", "height": "150", "fill": "#667eea"}}
    }},
    {{
      "component": "svg-text",
      "classes": ["label"],
      "attributes": {{"x": "70", "y": "370", "text-anchor": "middle"}},
      "text": "Jan"
    }}
  ]
}}

EXAMPLE DATA TABLE:
{{
  "component": "data-table",
  "classes": ["sales-table"],
  "data": {{
    "headers": ["Month", "Sales", "Growth"],
    "rows": [
      ["January", "$50,000", "+12%"],
      ["February", "$65,000", "+30%"]
    ]
  }}
}}

RULES:
1. Always include "schemaVersion": "1.0"
2. Every class you use MUST be defined in customStyles
3. Use valid CSS properties and values
4. Create responsive, modern designs
5. You can use pseudo-classes like ":hover" by defining them as separate keys (e.g., "button:hover")
6. You can define @keyframes for animations
7. For data tables, use the data-table component
8. For charts, build them using SVG components (svg, rect, circle, line, polyline, path, svg-text)
9. Output ONLY valid JSON, no explanations, no markdown

OUTPUT FORMAT (JSON only):
{{
  "schemaVersion": "1.0",
  "structure": {{ ... }},
  "customStyles": {{ ... }}
}}"""


# ============================================================================
# HTML CONVERTER
# ============================================================================

class HTMLConverter:
    def __init__(self, spec: Dict):
        self.spec = spec
    
    def convert(self, json_structure: Dict) -> str:
        body_html = self._render_node(json_structure["structure"])
        css = self._generate_css(json_structure.get("customStyles", {}))
        return self._wrap_in_document(body_html, css)
    
    def _render_node(self, node: Dict) -> str:
        component_def = self.spec["components"].get(node["component"])
        if not component_def:
            # Fallback to div if component not found
            return f"<div>Unknown component: {node['component']}</div>"
        
        # Handle special data-table component
        if component_def.get("special") == "table":
            return self._render_data_table(node)
        
        tag = self._get_tag(node, component_def)
        
        # Self-closing tags
        if component_def.get("selfClosing"):
            return self._render_self_closing(tag, node)
        
        # Opening tag
        html = f"<{tag}"
        
        # Add classes
        if node.get("classes"):
            html += f' class="{" ".join(node["classes"])}"'
        
        # Add attributes
        if node.get("attributes"):
            for key, value in node["attributes"].items():
                html += f' {key}="{self._escape_html(str(value))}"'
        
        html += ">"
        
        # Add text content
        if node.get("text"):
            html += self._escape_html(node["text"])
        
        # Add children
        if node.get("children"):
            for child in node["children"]:
                html += self._render_node(child)
        
        # Closing tag
        html += f"</{tag}>"
        
        return html
    
    def _render_self_closing(self, tag: str, node: Dict) -> str:
        html = f"<{tag}"
        
        if node.get("classes"):
            html += f' class="{" ".join(node["classes"])}"'
        
        if node.get("attributes"):
            for key, value in node["attributes"].items():
                html += f' {key}="{self._escape_html(str(value))}"'
        
        html += " />"
        return html
    
    def _render_data_table(self, node: Dict) -> str:
        """Render HTML table from data"""
        data = node.get("data", {})
        headers = data.get("headers", [])
        rows = data.get("rows", [])
        
        classes = " ".join(node.get("classes", []))
        
        html = f'<div class="{classes}">'
        html += '<table>'
        
        # Headers
        if headers:
            html += '<thead><tr>'
            for header in headers:
                html += f'<th>{self._escape_html(str(header))}</th>'
            html += '</tr></thead>'
        
        # Rows
        html += '<tbody>'
        for row in rows:
            html += '<tr>'
            for cell in row:
                html += f'<td>{self._escape_html(str(cell))}</td>'
            html += '</tr>'
        html += '</tbody>'
        
        html += '</table></div>'
        return html
    
    def _get_tag(self, node: Dict, component_def: Dict) -> str:
        # Handle components with dynamic tags (like heading)
        if node.get("props", {}).get("level"):
            return node["props"]["level"]
        
        # Handle list (ul vs ol)
        if node["component"] == "list":
            return "ol" if node.get("props", {}).get("ordered") else "ul"
        
        return component_def["tag"]
    
    def _generate_css(self, custom_styles: Dict) -> str:
        css = BASE_CSS
        
        # Add custom styles
        if custom_styles:
            css += "\n/* Custom Styles */\n"
            for class_name, rules in custom_styles.items():
                # Handle @keyframes and other @ rules
                if class_name.startswith("@"):
                    css += f"\n{class_name} {{\n"
                else:
                    # Add dot prefix if not present and not a pseudo-class
                    if ":" in class_name:
                        # It's a pseudo-class like "button:hover"
                        base = class_name.split(":")[0]
                        pseudo = class_name.split(":")[1]
                        selector = f".{base}:{pseudo}"
                    else:
                        selector = f".{class_name}" if not class_name.startswith(".") else class_name
                    css += f"\n{selector} {{\n"
                
                # Handle nested rules (for @keyframes)
                for property_name, value in rules.items():
                    if isinstance(value, dict):
                        # Nested rule (like keyframe percentages)
                        css += f"  {property_name} {{\n"
                        for nested_prop, nested_val in value.items():
                            nested_prop_kebab = self._camel_to_kebab(nested_prop)
                            css += f"    {nested_prop_kebab}: {nested_val};\n"
                        css += "  }\n"
                    else:
                        # Regular CSS property
                        property_kebab = self._camel_to_kebab(property_name)
                        css += f"  {property_kebab}: {value};\n"
                
                css += "}\n"
        
        return css
    
    def _camel_to_kebab(self, text: str) -> str:
        """Convert camelCase to kebab-case"""
        return re.sub(r'([A-Z])', r'-\1', text).lower()
    
    def _wrap_in_document(self, body_html: str, css: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Generated Page</title>
  <style>
{css}
  </style>
</head>
<body>
{body_html}
</body>
</html>"""
    
    def _escape_html(self, text: str) -> str:
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#039;"))


# ============================================================================
# LLM CLIENT
# ============================================================================

class LLMClient:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.system_prompt = get_system_prompt()
    
    def generate_json(self, user_request: str, current_json: Optional[Dict] = None) -> Dict:
        """Call LLM to generate or update JSON structure"""
        
        if current_json is None:
            # First request - provide the initial template
            user_message = f"""User wants to create a page: {user_request}

Here's a starting template you can modify:
{json.dumps(INITIAL_JSON_TEMPLATE, indent=2)}

Please update this template to match the user's request. Remember to define ALL classes in customStyles.
Return ONLY the JSON structure, no explanations."""
        else:
            # Subsequent requests - provide current structure
            user_message = f"""Current page structure:
{json.dumps(current_json, indent=2)}

User wants to update it: {user_request}

Please update the structure accordingly. Remember that every class you use must be defined in customStyles.
Return ONLY the JSON structure, no explanations."""
        
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            temperature=0.7,
            system=self.system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        # Extract JSON from response
        response_text = response.content[0].text
        
        # ADD THIS - Display response stats
        print("=" * 70)
        print(f"LLM RESPONSE STATS:")
        print(f"  Characters: {len(response_text):,}")
        print(f"  Lines: {len(response_text.splitlines()):,}")
        if hasattr(response, 'usage'):
            print(f"  Input tokens: {response.usage.input_tokens:,}")
            print(f"  Output tokens: {response.usage.output_tokens:,}")
            print(f"  Total tokens: {response.usage.input_tokens + response.usage.output_tokens:,}")
        print("=" * 70)
        
        # Try to parse JSON directly
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract from markdown
            json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', response_text)
            if json_match:
                return json.loads(json_match.group(1))
            else:
                raise ValueError("LLM response did not contain valid JSON")


# ============================================================================
# GENERATE HTML WITH DATA (FOR WEB SCRAPING INTEGRATION)
# ============================================================================

def _generate_html(
    user_query: str,
    search_results: Dict[str, List[Dict]] = None,
    scraped_results: List[Dict] = None,
    structured_data: Dict = None,
    current_json: Optional[Dict] = None,
    api_key: str = None,
    verbose: bool = False
) -> str:
    """
    Generate HTML with comprehensive context including scraped data.
    Uses JSON intermediate format for better structure.
    
    This function can be used standalone or integrated into your scraping pipeline.
    """
    
    # Build search context string
    search_context = ""
    if search_results:
        search_context = "\n\n=== WEB SEARCH RESULTS ===\n"
        for query, results in search_results.items():
            search_context += f"\nQuery: {query}\n"
            for i, result in enumerate(results, 1):
                search_context += f"\n{i}. {result['title']}\n"
                search_context += f"   URL: {result['link']}\n"
                search_context += f"   Snippet: {result['snippet']}\n"
    
    # Build scraped content context
    scraped_context = ""
    if scraped_results:
        scraped_context = "\n\n=== SCRAPED WEB CONTENT ===\n"
        scraped_context += "Complete content extracted from web pages.\n"
        
        successful_scrapes = [s for s in scraped_results if not s.get('error')]
        
        for i, scrape in enumerate(successful_scrapes, 1):
            scraped_context += f"\n--- Source {i}: {scrape['url']} ---\n"
            scraped_context += f"Relevance Score: {scrape.get('score', 0):.2f}\n"
            scraped_context += f"Word Count: {scrape.get('word_count', 0)}\n"
            
            # Add best chunk
            if scrape.get('best_chunk'):
                scraped_context += f"\nMost Relevant Content:\n"
                scraped_context += "```\n"
                scraped_context += scrape['best_chunk'][:3000]
                if len(scrape['best_chunk']) > 3000:
                    scraped_context += "\n... (truncated)"
                scraped_context += "\n```\n"
            
            # Add tables
            if scrape.get('tables') and scrape.get('tables_count', 0) > 0:
                scraped_context += f"\nExtracted Tables ({scrape['tables_count']} total):\n"
                for j, table in enumerate(scrape['tables'][:3], 1):  # Limit to 3 tables per source
                    scraped_context += f"\nTable {j}:\n"
                    scraped_context += "```json\n"
                    table_json = json.dumps(table, indent=2)
                    scraped_context += table_json[:2000]
                    if len(table_json) > 2000:
                        scraped_context += "\n... (truncated)"
                    scraped_context += "\n```\n"
    
    # Build structured data context
    structured_context = ""
    if structured_data:
        structured_context = "\n\n=== EXTRACTED STRUCTURED DATA ===\n"
        structured_context += json.dumps(structured_data, indent=2)
        structured_context += "\n\nUse these exact values in your app."
    
    # Get system prompt
    system_prompt = get_system_prompt()
    
    # Count data
    num_scraped = len([s for s in scraped_results if not s.get('error')]) if scraped_results else 0
    num_tables = sum(s.get('tables_count', 0) for s in scraped_results) if scraped_results else 0
    
    # Build user prompt
    if current_json:
        user_prompt = f"""Update the application structure based on this request:

USER REQUEST: {user_query}

CURRENT JSON STRUCTURE:
{json.dumps(current_json, indent=2)}
{search_context}
{scraped_context}
{structured_context}

Update the JSON structure to incorporate this new data and requirements.
Return ONLY valid JSON, no explanations."""
    else:
        user_prompt = f"""Create a comprehensive data-rich application based on this request:

USER REQUEST: {user_query}

DATA PROVIDED:
{search_context}
{scraped_context}
{structured_context}

YOUR TASK: Create a JSON structure for a beautiful, data-rich application.

DATA AVAILABLE:
- {num_scraped} scraped web pages
- {num_tables} data tables extracted
- Search results and structured data

REQUIREMENTS:

1. STRUCTURE:
   - Use "container" component as root
   - Create sections for: header, executive summary, key findings, data visualizations, sources
   - For each data table, create:
     * "data-table" component with the table data
     * SVG chart visualization using svg, rect, circle, line, polyline, path, svg-text components

2. DATA VISUALIZATION:
   For each table, create BOTH:
   a) data-table component:
   {{
     "component": "data-table",
     "classes": ["data-table"],
     "data": {{
       "headers": ["Column1", "Column2"],
       "rows": [["Value1", "Value2"]]
     }}
   }}
   
   b) SVG chart (bar/line/pie) using SVG components:
   {{
     "component": "svg",
     "classes": ["chart"],
     "attributes": {{"viewBox": "0 0 600 400"}},
     "children": [
       {{"component": "rect", "attributes": {{"x": "50", "y": "200", "width": "40", "height": "150", "fill": "#667eea"}}}},
       {{"component": "svg-text", "attributes": {{"x": "70", "y": "370"}}, "text": "Label"}}
     ]
   }}

3. STYLING:
   - Create modern, professional customStyles
   - Use gradients, shadows, cards
   - Responsive design
   - Professional color palette

4. OUTPUT:
   Return ONLY the JSON structure:
   {{
     "schemaVersion": "1.0",
     "structure": {{ ... }},
     "customStyles": {{ ... }}
   }}

Generate the JSON now."""
    
    # Generate with Claude
    start_time = datetime.now()
    
    if not api_key:
        api_key = os.getenv("ANTHROPIC_API_KEY")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    messages = [{"role": "user", "content": user_prompt}]
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        system=system_prompt,
        max_tokens=16000,
        temperature=0.7,
        messages=messages
    )
    
    duration = (datetime.now() - start_time).total_seconds()
    
    if verbose:
        print(f"API Response in {duration:.2f}s")
    
    # Extract JSON
    response_text = message.content[0].text
    
    # Try to parse JSON
    try:
        json_structure = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract from markdown
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', response_text)
        if json_match:
            json_structure = json.loads(json_match.group(1))
        else:
            raise ValueError("Failed to parse JSON from LLM response")
    
    # Convert JSON to HTML
    converter = HTMLConverter(SCHEMA_SPEC)
    html_content = converter.convert(json_structure)
    
    # Log summary
    if verbose:
        summary = f"Generated application with data visualizations."
        if search_results:
            total_results = sum(len(r) for r in search_results.values())
            summary += f" Used {len(search_results)} queries with {total_results} results."
        if scraped_results:
            successful = len([s for s in scraped_results if not s.get('error')])
            total_tables = sum(s.get('tables_count', 0) for s in scraped_results)
            summary += f" Processed {successful} pages with {total_tables} tables."
        print(summary)
    
    return html_content


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class HTMLAppGenerator:
    def __init__(self, api_key: str):
        self.llm_client = LLMClient(api_key)
        self.converter = HTMLConverter(SCHEMA_SPEC)
        self.current_json: Optional[Dict] = None
        self.conversation_history: List[Dict] = []
    
    def process_request(self, user_request: str, max_attempts: int = 3) -> Dict:
        """Process a user request and return HTML + metadata"""
        
        attempts = 0
        last_error = None
        
        while attempts < max_attempts:
            try:
                # Generate JSON from LLM
                json_structure = self.llm_client.generate_json(
                    user_request,
                    self.current_json
                )
                
                # Store valid JSON
                self.current_json = json_structure
                
         
                
                # Convert to HTML
                html = self.converter.convert(json_structure)
                
                # Store in conversation history
                self.conversation_history.append({
                    "request": user_request,
                    "json": json_structure,
                    "success": True
                })
                
                return {
                    "success": True,
                    "html": html,
                    "json": json_structure,
                    "attempts": attempts + 1
                }
                
            except json.JSONDecodeError as e:
                print(f"Attempt {attempts + 1}: JSON Deserialization Error")
                print(f"  Error: {str(e)}")
                print(f"  Line {e.lineno}, Column {e.colno}")
                
                # Feed error back to LLM
                user_request = f"""Your previous response had a JSON syntax error:
Line {e.lineno}, Column {e.colno}: {str(e)}

Common issues:
- Missing or extra commas
- Unclosed brackets or braces
- Unescaped quotes in text content
- Trailing commas

Please regenerate valid, complete JSON."""
                attempts += 1
                last_error = str(e)
                
            except KeyError as e:
                print(f"Attempt {attempts + 1}: Missing required field")
                print(f"  Error: {str(e)}")
                
                user_request = f"""Your previous JSON was missing a required field: {str(e)}

Please ensure the JSON has:
- "schemaVersion": "1.0"
- "structure": {{ ... }}
- "customStyles": {{ ... }}

Regenerate complete JSON."""
                attempts += 1
                last_error = str(e)
                
            except Exception as e:
                print(f"Attempt {attempts + 1}: Unexpected Error - {str(e)}")
                attempts += 1
                last_error = str(e)
                
                if attempts >= max_attempts:
                    return {
                        "success": False,
                        "error": f"Failed after {max_attempts} attempts: {last_error}",
                        "attempts": attempts
                    }
        
        return {
            "success": False,
            "error": f"Failed after {max_attempts} attempts: {last_error}",
            "attempts": attempts
        }
    
    def export_json(self) -> Optional[Dict]:
        """Export current JSON structure"""
        return self.current_json
    
    def import_json(self, json_structure: Dict) -> Tuple[bool, str]:
        """Import JSON structure"""
        try:
            # Just try to convert it
            self.converter.convert(json_structure)
            self.current_json = json_structure
            return True, "JSON imported successfully"
        except Exception as e:
            return False, f"Invalid JSON: {str(e)}"
    
    def get_html(self) -> Optional[str]:
        """Get HTML for current structure"""
        if self.current_json is None:
            return None
        return self.converter.convert(self.current_json)


# ============================================================================
# INTERACTIVE CLI
# ============================================================================

def interactive_mode():
    """Run interactive CLI mode"""
    
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it with: export ANTHROPIC_API_KEY='your-key-here'")
        return
    
    print("=" * 70)
    print("HTML APP GENERATOR - Interactive Mode")
    print("=" * 70)
    print("\nCommands:")
    print("  - Type your request to generate/update HTML")
    print("  - 'save <filename>' - Save current HTML to file")
    print("  - 'json' - Show current JSON structure")
    print("  - 'export <filename>' - Export JSON to file")
    print("  - 'import <filename>' - Import JSON from file")
    print("  - 'reset' - Start fresh")
    print("  - 'quit' - Exit")
    print("\n" + "=" * 70)
    
    generator = HTMLAppGenerator(api_key)
    
    while True:
        try:
            user_input = input("\n>>> ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() == 'quit':
                print("Goodbye!")
                break
            
            elif user_input.lower() == 'reset':
                generator.current_json = None
                generator.conversation_history = []
                print("✓ Reset complete. Starting fresh.")
                continue
            
            elif user_input.lower() == 'json':
                if generator.current_json:
                    print(json.dumps(generator.current_json, indent=2))
                else:
                    print("No JSON structure yet. Make a request first.")
                continue
            
            elif user_input.lower().startswith('save '):
                filename = user_input[5:].strip()
                html = generator.get_html()
                if html:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(html)
                    print(f"✓ HTML saved to {filename}")
                else:
                    print("No HTML to save. Make a request first.")
                continue
            
            elif user_input.lower().startswith('export '):
                filename = user_input[7:].strip()
                json_data = generator.export_json()
                if json_data:
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, indent=2)
                    print(f"✓ JSON exported to {filename}")
                else:
                    print("No JSON to export. Make a request first.")
                continue
            
            elif user_input.lower().startswith('import '):
                filename = user_input[7:].strip()
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                    success, message = generator.import_json(json_data)
                    if success:
                        print(f"✓ {message}")
                    else:
                        print(f"✗ {message}")
                except Exception as e:
                    print(f"✗ Error importing: {str(e)}")
                continue
            
            # Process as regular request
            print("\nProcessing request...")
            result = generator.process_request(user_input)
            
            if result["success"]:
                print(f"\n✓ Success! (took {result['attempts']} attempt(s))")
                print(f"\nGenerated {len(result['html'])} characters of HTML")
                
                # Offer to show HTML
                show = input("\nShow HTML? (y/n): ").strip().lower()
                if show == 'y':
                    print("\n" + "=" * 70)
                    print(result['html'])
                    print("=" * 70)
            else:
                print(f"\n✗ Failed: {result['error']}")
        
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n✗ Error: {str(e)}")


# ============================================================================
# PROGRAMMATIC API EXAMPLE
# ============================================================================

def api_example():
    """Example of using the generator programmatically"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        return
    
    # Initialize generator
    generator = HTMLAppGenerator(api_key)
    
    # Generate initial page
    result1 = generator.process_request(
        "Create a landing page for a SaaS product with a hero section, features, and CTA"
    )
    
    if result1["success"]:
        print("Initial page generated!")
        with open("output1.html", "w", encoding='utf-8') as f:
            f.write(result1["html"])
        print("Saved to output1.html")
    
    # Update the page
    result2 = generator.process_request(
        "Add a pricing section with 3 tiers"
    )
    
    if result2["success"]:
        print("Page updated!")
        with open("output2.html", "w", encoding='utf-8') as f:
            f.write(result2["html"])
        print("Saved to output2.html")
    
    # Export JSON
    json_data = generator.export_json()
    with open("structure.json", "w", encoding='utf-8') as f:
        json.dump(json_data, f, indent=2)
    print("JSON exported to structure.json")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "example":
        api_example()
    else:
        interactive_mode()