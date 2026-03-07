import pandas as pd


def calculate_ema(df, price_column='Close'):
    """
    Calculate EMA20 and EMA50 for a dataframe.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Input dataframe with price data
    price_column : str
        Name of the column to calculate EMA on (default: 'Close')
    
    Returns:
    --------
    pandas.DataFrame
        Dataframe with added EMA20 and EMA50 columns
    """
    df['EMA50'] = df[price_column].ewm(span=5, adjust=False).mean()
    df['EMA20'] = df[price_column].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df[price_column].ewm(span=50, adjust=False).mean()
    
    
    return df
