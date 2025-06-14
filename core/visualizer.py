import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import json
from datetime import datetime

class CallGraphVisualizer:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('CallGraphVisualizer')

    def generate_html_report(self, json_file: str) -> str:
        """生成HTML格式的调用图报告
        
        Args:
            json_file: JSON文件路径
            
        Returns:
            生成的HTML报告文件路径
        """
        try:
            # 读取JSON数据
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 准备ECharts数据
            nodes = []
            links = []
            
            # 处理节点
            for node in data['nodes']:
                nodes.append({
                    'id': node['id'],
                    'name': node['name'],
                    'symbolSize': min(30, 10 + node['call_count']),  # 根据调用次数调整节点大小
                    'value': node['call_count'],
                    'category': 0
                })
            
            # 处理边
            for edge in data['edges']:
                links.append({
                    'source': edge['source'],
                    'target': edge['target'],
                    'value': edge['call_count'],
                    'lineStyle': {
                        'width': min(5, 1 + edge['call_count'] / 10)  # 根据调用次数调整边宽度
                    }
                })
            
            # 生成HTML内容
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Function Call Graph Report</title>
                <meta charset="utf-8">
                <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
                <style>
                    body {{ 
                        font-family: Arial, sans-serif; 
                        margin: 20px;
                        background-color: #f5f5f5;
                    }}
                    .container {{ 
                        max-width: 1400px; 
                        margin: 0 auto;
                        background-color: white;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                        padding-bottom: 20px;
                        border-bottom: 1px solid #eee;
                    }}
                    .graph-container {{
                        margin: 20px 0;
                        padding: 20px;
                        background-color: white;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        height: 800px;  /* 设置图表容器高度 */
                    }}
                    .stats {{ 
                        margin: 20px 0;
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                        gap: 20px;
                    }}
                    .stat-card {{
                        background-color: white;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .stat-card h3 {{
                        margin-top: 0;
                        color: #333;
                        border-bottom: 2px solid #eee;
                        padding-bottom: 10px;
                    }}
                    table {{ 
                        width: 100%;
                        border-collapse: collapse;
                        margin: 10px 0;
                    }}
                    th, td {{ 
                        padding: 12px;
                        text-align: left;
                        border-bottom: 1px solid #eee;
                    }}
                    th {{ 
                        background-color: #f8f9fa;
                        font-weight: bold;
                    }}
                    tr:hover {{ 
                        background-color: #f5f5f5;
                    }}
                    .controls {{
                        margin: 20px 0;
                        padding: 15px;
                        background-color: #f8f9fa;
                        border-radius: 8px;
                        display: flex;
                        gap: 10px;
                        flex-wrap: wrap;
                    }}
                    .search-box {{
                        padding: 8px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        flex-grow: 1;
                    }}
                    .tooltip {{
                        background-color: rgba(255, 255, 255, 0.9);
                        border: 1px solid #ccc;
                        border-radius: 4px;
                        padding: 10px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Function Call Graph Report</h1>
                        <p>Generated at: {data['metadata']['end_time']}</p>
                    </div>
                    
                    <div class="controls">
                        <input type="text" id="searchBox" class="search-box" placeholder="Search functions...">
                    </div>
                    
                    <div class="stats">
                        <div class="stat-card">
                            <h3>Statistics</h3>
                            <table>
                                <tr>
                                    <td>Total Calls</td>
                                    <td>{data['metadata']['total_calls']}</td>
                                </tr>
                                <tr>
                                    <td>Unique Functions</td>
                                    <td>{data['metadata']['unique_functions']}</td>
                                </tr>
                                <tr>
                                    <td>Unique Call Relationships</td>
                                    <td>{data['metadata']['unique_calls']}</td>
                                </tr>
                                <tr>
                                    <td>Start Time</td>
                                    <td>{data['metadata']['start_time']}</td>
                                </tr>
                                <tr>
                                    <td>End Time</td>
                                    <td>{data['metadata']['end_time']}</td>
                                </tr>
                            </table>
                        </div>
                        
                        <div class="stat-card">
                            <h3>Most Called Functions</h3>
                            <table>
                                <tr>
                                    <th>Function</th>
                                    <th>Calls</th>
                                </tr>
                                {self._generate_function_table_rows(sorted(data['nodes'], key=lambda x: x['call_count'], reverse=True)[:10])}
                            </table>
                        </div>
                    </div>
                    
                    <div class="graph-container" id="graph"></div>
                </div>

                <script>
                    // 初始化ECharts实例
                    var chartDom = document.getElementById('graph');
                    var myChart = echarts.init(chartDom);
                    
                    // 准备数据
                    var nodes = {json.dumps(nodes)};
                    var links = {json.dumps(links)};
                    
                    // 配置项
                    var option = {{
                        tooltip: {{
                            trigger: 'item',
                            formatter: function(params) {{
                                if (params.dataType === 'node') {{
                                    return `<div class="tooltip">
                                        <strong>${{params.data.name}}</strong><br/>
                                        Call Count: ${{params.data.value}}
                                    </div>`;
                                }} else {{
                                    return `<div class="tooltip">
                                        <strong>${{params.data.source}} → ${{params.data.target}}</strong><br/>
                                        Call Count: ${{params.data.value}}
                                    </div>`;
                                }}
                            }}
                        }},
                        legend: {{
                            show: false
                        }},
                        animationDuration: 1500,
                        animationEasingUpdate: 'quinticInOut',
                        series: [{{
                            type: 'graph',
                            layout: 'force',
                            data: nodes,
                            links: links,
                            categories: [{{
                                name: 'Function'
                            }}],
                            roam: true,
                            label: {{
                                show: true,
                                position: 'right',
                                formatter: '{{b}}',
                                fontSize: 12,
                                backgroundColor: 'rgba(255, 255, 255, 0.7)',
                                padding: [4, 8],
                                borderRadius: 4
                            }},
                            force: {{
                                repulsion: 200,
                                edgeLength: [80, 200],
                                gravity: 0.2,
                                layoutAnimation: true
                            }},
                            lineStyle: {{
                                color: '#666',
                                curveness: 0.3,
                                width: 2,
                                opacity: 0.7
                            }},
                            edgeSymbol: ['none', 'arrow'],
                            edgeSymbolSize: [0, 8],
                            edgeLabel: {{
                                show: true,
                                formatter: function(params) {{
                                    return params.data.value;
                                }},
                                fontSize: 10,
                                backgroundColor: 'rgba(255, 255, 255, 0.7)',
                                padding: [2, 4],
                                borderRadius: 2
                            }},
                            itemStyle: {{
                                color: '#5470c6',
                                borderColor: '#fff',
                                borderWidth: 2,
                                shadowColor: 'rgba(0, 0, 0, 0.2)',
                                shadowBlur: 10
                            }},
                            emphasis: {{
                                focus: 'adjacency',
                                lineStyle: {{
                                    width: 4,
                                    opacity: 1
                                }},
                                edgeLabel: {{
                                    show: true,
                                    fontSize: 12,
                                    backgroundColor: 'rgba(255, 255, 255, 0.9)'
                                }},
                                itemStyle: {{
                                    shadowBlur: 20
                                }}
                            }}
                        }}]
                    }};
                    
                    // 使用配置项
                    myChart.setOption(option);
                    
                    // 搜索功能
                    document.getElementById('searchBox').addEventListener('input', function(e) {{
                        const searchText = e.target.value.toLowerCase();
                        const option = myChart.getOption();
                        
                        option.series[0].data.forEach(node => {{
                            const name = node.name.toLowerCase();
                            if (name.includes(searchText)) {{
                                node.itemStyle = {{ color: '#ffeb3b' }};
                            }} else {{
                                node.itemStyle = {{ color: '#5470c6' }};
                            }}
                        }});
                        
                        myChart.setOption(option);
                    }});
                    
                    // 响应窗口大小变化
                    window.addEventListener('resize', function() {{
                        myChart.resize();
                    }});
                </script>
            </body>
            </html>
            """
            
            # 保存HTML文件
            output_file = self.output_dir / f"call_graph_report_{Path(json_file).stem}.html"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"HTML report saved to {output_file}")
            return str(output_file)
            
        except Exception as e:
            self.logger.error(f"Failed to generate HTML report: {e}")
            raise

    def _generate_function_table_rows(self, nodes: list) -> str:
        """生成函数表格的HTML行"""
        rows = []
        for node in nodes:
            name = node['name']
            rows.append(f"""
                <tr>
                    <td>{name}</td>
                    <td>{node['call_count']}</td>
                </tr>
            """)
        return '\n'.join(rows) 