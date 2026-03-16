import glob
from tqdm import tqdm # 进度条库，pip install tqdm

# 继承上面的类或直接使用
def scan_market(tdx_path):
    engine = TdxLocalEngine(tdx_path)
    
    # 获取所有上海市场的股票文件
    # 路径通配符：.../vipdoc/sh/lday/*.day
    search_path = os.path.join(tdx_path, "vipdoc", "sh", "lday", "*.day")
    file_list = glob.glob(search_path)
    
    selected_stocks = []
    
    print(f"🚀 开始扫描 {len(file_list)} 只股票...")
    
    # 使用 tqdm 显示进度条
    for file_path in tqdm(file_list):
        # 从文件名提取代码: ...\sh600000.day -> 600000
        file_name = os.path.basename(file_path)
        code = file_name[2:8] # 去掉sh和.day
        
        # 读取数据
        df = engine.get_stock_daily("sh", code)
        
        if df is None or len(df) < 30: # 剔除新股或数据不足的
            continue
            
        # === 核心策略逻辑 (Strategy Logic) ===
        
        # 1. 计算技术指标
        # 计算5日和20日均线
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        # 计算5日平均成交量
        df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
        
        # 取最近一天的数据
        today = df.iloc[-1]
        yesterday = df.iloc[-2]
        
        # 2. 选股条件
        # 条件A: 站上20日线 (趋势向上)
        cond_trend = today['Close'] > today['MA20']
        
        # 条件B: 倍量 (今日成交量 > 2倍的5日均量) -> 资金入场迹象
        cond_vol = today['Volume'] > (2 * yesterday['Vol_MA5'])
        
        # 条件C: 涨幅大于3%且小于9.5% (剔除一字板)
        pct_change = (today['Close'] - yesterday['Close']) / yesterday['Close']
        cond_price = 0.03 < pct_change < 0.095
        
        # === 满足所有条件 ===
        if cond_trend and cond_vol and cond_price:
            selected_stocks.append({
                '代码': code,
                '日期': today.name.strftime('%Y-%m-%d'),
                '收盘价': today['Close'],
                '涨幅%': round(pct_change * 100, 2),
                '倍量系数': round(today['Volume'] / yesterday['Vol_MA5'], 2)
            })

    # 输出结果
    result_df = pd.DataFrame(selected_stocks)
    if not result_df.empty:
        print("\n🏆 选股结果：")
        print(result_df)
        result_df.to_excel("今日选股结果.xlsx", index=False)
    else:
        print("今天没有符合条件的股票。")

# 运行扫描
if __name__ == "__main__":
    TDX_ROOT = r"E:\Tongdaxin"
    scan_market(TDX_ROOT)