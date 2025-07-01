"""
DeepSeek AI API Client

Provides methods for interacting with DeepSeek AI API for professional
market analysis and trading insights.
"""

import json
from typing import Dict, Any, Optional, List

from .base_client import BaseAPIClient
from ..config import Config
from ..exceptions import DeepSeekAPIError


class DeepSeekClient(BaseAPIClient):
    """DeepSeek AI API client for market analysis"""
    
    def __init__(self, config: Config):
        """
        Initialize DeepSeek client.
        
        Args:
            config: Configuration object containing API credentials
        """
        super().__init__(config, "DeepSeek")
        
        self.api_url = config.api.deepseek_url
        self.api_key = config.api.deepseek_api_key
        
        # Update session headers with auth
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
    
    def test_connection(self) -> bool:
        """
        Test DeepSeek API connection and authentication.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Make a simple test request
            response = self.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            
            if response and 'choices' in response:
                self.logger.info("DeepSeek API connection test successful")
                return True
            else:
                self.logger.error("DeepSeek API connection test failed: Invalid response")
                return False
                
        except Exception as e:
            self.logger.error(f"DeepSeek API connection test failed: {e}")
            return False
    
    def get_api_info(self) -> Dict[str, Any]:
        """
        Get DeepSeek API information and status.
        
        Returns:
            Dictionary containing API information
        """
        try:
            # DeepSeek doesn't have a dedicated info endpoint
            # So we make a minimal request to check status
            test_response = self.chat_completion(
                messages=[{"role": "user", "content": "API status check"}],
                max_tokens=5
            )
            
            if test_response:
                return {
                    "name": "DeepSeek",
                    "status": "operational",
                    "model": "deepseek-chat",
                    "api_version": "v1"
                }
            else:
                return {
                    "name": "DeepSeek",
                    "status": "error",
                    "error": "Failed to get API response"
                }
                
        except Exception as e:
            return {
                "name": "DeepSeek",
                "status": "error",
                "error": str(e)
            }
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek-chat",
        max_tokens: int = None,
        temperature: float = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Make a chat completion request to DeepSeek API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model name to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            **kwargs: Additional parameters
            
        Returns:
            API response dictionary or None if failed
            
        Raises:
            DeepSeekAPIError: For API-related errors
        """
        max_tokens = max_tokens or self.config.analysis.ai_max_tokens
        temperature = temperature or self.config.analysis.ai_temperature
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        try:
            self.logger.debug(f"Making DeepSeek chat completion request")
            
            response = self.post(
                url=self.api_url,
                data=payload
            )
            
            response_data = response.json()
            
            # Validate response structure
            if 'choices' not in response_data:
                raise DeepSeekAPIError(
                    "Invalid response format: missing 'choices'",
                    response.status_code,
                    "invalid_response",
                    response_data
                )
            
            if not response_data['choices']:
                raise DeepSeekAPIError(
                    "Empty choices in response",
                    response.status_code,
                    "empty_choices",
                    response_data
                )
            
            self.logger.debug("DeepSeek chat completion successful")
            return response_data
            
        except DeepSeekAPIError:
            # Re-raise our custom exceptions
            raise
            
        except Exception as e:
            raise DeepSeekAPIError(
                f"Unexpected error in chat completion: {str(e)}"
            )
    
    def analyze_market_data(self, analysis_data: Dict[str, Any]) -> str:
        """
        Send market analysis data to DeepSeek for professional insights.
        
        Args:
            analysis_data: Comprehensive market analysis data
            
        Returns:
            AI-generated market analysis text
            
        Raises:
            DeepSeekAPIError: For API-related errors
        """
        try:
            # Create the analysis prompt
            prompt = self._create_analysis_prompt(analysis_data)
            
            # Make the API request
            response = self.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.analysis.ai_max_tokens,
                temperature=self.config.analysis.ai_temperature
            )
            
            if not response or 'choices' not in response:
                raise DeepSeekAPIError("Invalid response from DeepSeek API")
            
            # Extract the analysis text
            analysis_text = response['choices'][0]['message']['content']
            
            self.logger.info("Market analysis completed successfully")
            return analysis_text
            
        except DeepSeekAPIError:
            # Re-raise our custom exceptions
            raise
            
        except Exception as e:
            self.logger.error(f"Market analysis failed: {e}")
            raise DeepSeekAPIError(f"Market analysis failed: {str(e)}")
    
    def _create_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """
        Create a comprehensive analysis prompt for the AI.
        
        Args:
            data: Market analysis data
            
        Returns:
            Formatted prompt string
        """
        prompt = (
            "## Binance资金流向专业分析任务\n\n"
            "我已收集了Binance现货和期货市场过去50根5分钟K线的资金流向数据（已剔除最新未完成的一根），包括：\n"
            "- 各交易对的资金流向趋势分析\n"
            "- 价格所处阶段预测（顶部、底部、上涨中、下跌中、整理中）\n"
            "- 订单簿数据（买卖盘不平衡度）\n"
            "- 资金压力分析\n"
            "- 异常交易检测\n\n"

            "请从专业交易员和机构投资者角度进行深度分析：\n\n"

            "1. **主力资金行为解读**：\n"
            "   - 通过资金流向趋势变化，识别主力资金的建仓、出货行为\n"
            "   - 结合订单簿数据，分析主力资金的意图（吸筹、出货、洗盘等）\n"
            "   - 特别关注资金流向与价格变化不匹配的异常情况\n\n"

            "2. **价格阶段判断**：\n"
            "   - 根据资金流向趋势和价格关系，判断各交易对处于什么阶段（顶部、底部、上涨中、下跌中、整理中）\n"
            "   - 提供判断的置信度和依据\n"
            "   - 对比不同交易对的阶段差异，分析可能的轮动关系\n\n"

            "3. **短期趋势预判**：\n"
            "   - 基于资金流向和资金压力分析，预判未来4-8小时可能的价格走势\n"
            "   - 识别可能的反转信号或趋势延续信号\n"
            "   - 关注异常交易数据可能暗示的短期行情变化\n\n"

            "4. **交易策略建议**：\n"
            "   - 针对每个交易对，给出具体的交易建议（观望、做多、做空、减仓等）\n"
            "   - 提供可能的入场点位和止损位\n"
            "   - 评估风险和回报比\n\n"

            "请使用专业术语，保持分析简洁但深入，避免泛泛而谈。数据如下：\n\n" +
            json.dumps(data, indent=2, ensure_ascii=False) +
            "\n\n回复格式要求：中文，使用markdown格式，重点突出，适当使用表格对比分析。"
        )
        
        return prompt
    
    def get_simple_analysis(self, question: str, context: str = "") -> str:
        """
        Get a simple analysis response for a specific question.
        
        Args:
            question: Question to ask the AI
            context: Optional context information
            
        Returns:
            AI response text
        """
        try:
            prompt = f"{context}\n\n{question}" if context else question
            
            response = self.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7
            )
            
            if response and 'choices' in response:
                return response['choices'][0]['message']['content']
            else:
                return "无法获取AI分析结果"
                
        except Exception as e:
            self.logger.error(f"Simple analysis failed: {e}")
            return f"分析出错: {str(e)}"
    
    def stream_analysis(
        self, 
        analysis_data: Dict[str, Any],
        callback=None
    ) -> str:
        """
        Stream market analysis with real-time updates.
        
        Args:
            analysis_data: Market analysis data
            callback: Optional callback function for streaming updates
            
        Returns:
            Complete analysis text
        """
        # Note: This would require streaming support from the API
        # For now, we'll implement it as a regular request
        return self.analyze_market_data(analysis_data)
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get API usage statistics if available.
        
        Returns:
            Dictionary containing usage information
        """
        # DeepSeek doesn't provide usage stats endpoint
        # This is a placeholder for future implementation
        return {
            "status": "not_available",
            "message": "Usage stats not available from DeepSeek API"
        }