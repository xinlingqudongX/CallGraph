import json
import logging
import re
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import networkx as nx
from datetime import datetime

@dataclass
class FunctionNode:
    name: str
    call_count: int = 0

@dataclass
class FunctionEdge:
    source: str
    target: str
    call_count: int = 0

class CallGraphProcessor:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('CallGraphProcessor')
        
        # 初始化图
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, FunctionNode] = {}
        self.edges: Dict[tuple, FunctionEdge] = {}
        
        # 统计数据
        self.total_calls = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        # 堆栈解析正则表达式
        self.stack_pattern = re.compile(r'at\s+([^(]+)\(([^)]+)\)')

    def parse_stack_trace(self, stack_trace: str) -> List[Tuple[str, str]]:
        """解析堆栈信息，提取调用关系
        
        Args:
            stack_trace: 堆栈文本
            
        Returns:
            调用关系列表，每个元素为 (调用者, 被调用者) 的元组
        """
        calls = []
        lines = re.split(r'\n\t?',stack_trace)
        
        # 跳过第一行（当前方法）
        for i in range(1, len(lines)-1):
            current_line = lines[i].strip()
            next_line = lines[i+1].strip() if i+1 < len(lines) else None
            
            if not current_line or not next_line:
                continue
                
            current_match = self.stack_pattern.search(current_line)
            next_match = self.stack_pattern.search(next_line)
            
            if current_match and next_match:
                caller = next_match.group(1).strip()
                # caller_module = next_match.group(2).strip()
                callee = current_match.group(1).strip()
                # callee_module = current_match.group(2).strip()
                
                # 过滤掉系统类
                # if not any(x in caller_module for x in ['java.', 'android.', 'kotlin.']):
                calls.append((caller, callee))
        
        return calls

    def process_stack_trace(self, record: Dict[str, Any]) -> None:
        """处理堆栈信息记录
        
        Args:
            record: 包含堆栈信息的记录
        """
        if not self.start_time:
            self.start_time = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
        
        self.end_time = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
        
        if 'data' not in record or 'stackTrace' not in record['data']:
            return
            
        stack_trace = record['data']['stackTrace']
        calls = self.parse_stack_trace(stack_trace)
        
        for caller, callee in calls:
            self.total_calls += 1
            
            # 处理调用者节点
            if caller not in self.nodes:
                self.nodes[caller] = FunctionNode(
                    name=caller,
                )
            self.nodes[caller].call_count += 1

            # 处理被调用者节点
            if callee not in self.nodes:
                self.nodes[callee] = FunctionNode(
                    name=callee,
                )
            self.nodes[callee].call_count += 1

            # 处理边（调用关系）
            edge_key = (caller, callee)
            if edge_key not in self.edges:
                self.edges[edge_key] = FunctionEdge(
                    source=caller,
                    target=callee
                )
            self.edges[edge_key].call_count += 1

            # 更新图
            self.graph.add_edge(
                caller,
                callee,
                call_count=self.edges[edge_key].call_count
            )

    def process_call_record(self, record: Dict[str, Any]) -> None:
        """处理调用记录
        
        Args:
            record: 调用记录
        """
        if record.get('logType') == 'stack_trace':
            self.process_stack_trace(record)
        else:
            # 处理其他类型的记录
            if 'data' in record and all(k in record['data'] for k in ['caller', 'callee']):
                data = record['data']
                if not self.start_time:
                    self.start_time = datetime.fromtimestamp(record['timestamp'] / 1000)
                
                self.end_time = datetime.fromtimestamp(record['timestamp'] / 1000)
                self.total_calls += 1

                # 处理调用者节点
                caller_id = data['caller']
                if caller_id not in self.nodes:
                    self.nodes[caller_id] = FunctionNode(
                        name=data['caller'],
                    )
                self.nodes[caller_id].call_count += 1

                # 处理被调用者节点
                callee_id = data['callee']
                if callee_id not in self.nodes:
                    self.nodes[callee_id] = FunctionNode(
                        name=data['callee'],
                    )
                self.nodes[callee_id].call_count += 1

                # 处理边（调用关系）
                edge_key = (caller_id, callee_id)
                if edge_key not in self.edges:
                    self.edges[edge_key] = FunctionEdge(
                        source=caller_id,
                        target=callee_id
                    )
                self.edges[edge_key].call_count += 1

                # 更新图
                self.graph.add_edge(
                    caller_id,
                    callee_id,
                    call_count=self.edges[edge_key].call_count
                )

    def generate_graph(self) -> nx.DiGraph:
        """生成调用图"""
        # 添加节点属性
        for node_id, node in self.nodes.items():
            self.graph.add_node(
                node_id,
                name=node.name,
                call_count=node.call_count
            )
        
        return self.graph

    def save_graph(self, format: str = 'json') -> str:
        """保存调用图
        
        Args:
            format: 保存格式 ('json' 或 'graphml')
            
        Returns:
            保存的文件路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'json':
            # 转换为可序列化的格式
            graph_data = {
                'nodes': [
                    {
                        'id': node_id,
                        'name': data['name'],
                        'call_count': data['call_count']
                    }
                    for node_id, data in self.graph.nodes(data=True)
                ],
                'edges': [
                    {
                        'source': source,
                        'target': target,
                        'call_count': data['call_count']
                    }
                    for source, target, data in self.graph.edges(data=True)
                ],
                'metadata': {
                    'total_calls': self.total_calls,
                    'unique_functions': len(self.nodes),
                    'unique_calls': len(self.edges),
                    'start_time': self.start_time.isoformat() if self.start_time else None,
                    'end_time': self.end_time.isoformat() if self.end_time else None
                }
            }
            
            output_file = self.output_dir / f'call_graph_{timestamp}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Call graph saved to {output_file}")
            return str(output_file)
        
        elif format == 'graphml':
            output_file = self.output_dir / f'call_graph_{timestamp}.graphml'
            nx.write_graphml(self.graph, output_file)
            self.logger.info(f"Call graph saved to {output_file}")
            return str(output_file)
        
        else:
            raise ValueError(f"Unsupported format: {format}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        # 按调用次数排序的函数列表
        sorted_functions = sorted(
            self.nodes.items(),
            key=lambda x: x[1].call_count,
            reverse=True
        )

        return {
            'total_calls': self.total_calls,
            'unique_functions': len(self.nodes),
            'unique_calls': len(self.edges),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'most_called_functions': sorted_functions[:10],  # 前10个最常调用的函数
            'call_relationships': [
                {
                    'source': edge.source,
                    'target': edge.target,
                    'call_count': edge.call_count
                }
                for edge in sorted(
                    self.edges.values(),
                    key=lambda x: x.call_count,
                    reverse=True
                )[:10]  # 前10个最常见的调用关系
            ]
        } 