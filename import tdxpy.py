import os
import pandas as pd
from pytdx.reader import TdxDailyBarReader

class TdxLocalEngine:
    def __init__(self, tdx_path):
        self.tdx_path = tdx_path
        self.reader = TdxDailyBarReader()
        
    def get_stock_daily(self, market_code, stock_code):
        """
        读取单只股票的本地日线数据
        :param market_code: 'sh' (上海) 或 'sz' (深圳)
        :param stock_code: 股票代码，如 '600000'
        :return: DataFrame
        """
        # 拼接路径：安装目录/vipdoc/{market}/lday/{market}{code}.day
        file_name = f"{market_code}{stock_code}.day"
        file_path = os.path.join(self.tdx_path, "vipdoc", market_code, "lday", file_name)
        
        if not os.path.exists(file_path):
            return None
            
        try:
            # 1. 解析二进制文件
            df = self.reader.get_df(file_path)
            
            # 2. 数据清洗 (Data Cleaning)
            # 重命名列以符合量化习惯 (Open, High, Low, Close, Volume, Amount)
            df = df.rename(columns={
                'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close',
                'vol': 'Volume', 'amount': 'Amount', 'date': 'Date'
            })
            
            # 设置日期为索引，方便切片
            df.index = pd.to_datetime(df['Date'])
            df = df.drop(columns=['Date'])
            
            # 3. 数值调整 (Volume是股数，Amount是元，通常转为“手”和“万元”更易读)
            # df['Volume'] = df['Volume'] / 100  # 转为手
            # df['Amount'] = df['Amount'] / 10000 # 转为万元
            
            return df
        except Exception as e:
            print(f"解析错误 {file_path}: {e}")
            return None

# --- 使用示例 ---
if __name__ == "__main__":
    # 替换你的通达信路径
    TDX_ROOT = r"E:\Tongdaxin" 
    engine = TdxLocalEngine(TDX_ROOT)
    
    # 读取 浦发银行 (上海 600000)
    df = engine.get_stock_daily("sh", "600000")
    
    if df is not None:
        print("✅ 浦发银行数据解析成功：")
        print(df.tail()) # 打印最后5天