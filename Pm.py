import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from scipy import stats
from scipy.optimize import minimize
import yfinance as yf
from datetime import datetime, timedelta
from user_data import load_user_data, save_user_data
import requests

def get_stock_value(ticker, quantity):
    try:
        stock = yf.Ticker(ticker)
        current_price = stock.info.get('regularMarketPrice')
        if current_price is None:
            current_price = stock.history(period="1d")['Close'].iloc[-1]
        return current_price * quantity
    except Exception as e:
        st.error(f"Error fetching stock value for {ticker}: {e}")
        return 0

def perform_portfolio_overview(portfolio_returns, returns, portfolio):
    st.header("Portfolio Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Current Allocation")
        display_current_portfolio(portfolio)
    
    with col2:
        st.subheader("Key Metrics")
        metrics = calculate_portfolio_metrics(portfolio_returns)
        display_portfolio_metrics(metrics)
    
    st.subheader("Portfolio Returns Over Time")
    plot_portfolio_returns(portfolio_returns.index, portfolio_returns)

def display_current_portfolio(portfolio):
    if portfolio:
        df = pd.DataFrame(list(portfolio.items()), columns=['Stock', 'Quantity'])
        df['Value'] = df.apply(lambda row: get_stock_value(row['Stock'], row['Quantity']), axis=1)
        total_value = df['Value'].sum()
        df['Percentage'] = df['Value'] / total_value * 100 if total_value > 0 else 0
        
        fig = go.Figure(data=[go.Pie(labels=df['Stock'], values=df['Value'], hole=.3)])
        fig.update_layout(title='Portfolio Composition')
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df.style.format({'Quantity': '{:,.0f}', 'Value': '${:,.2f}', 'Percentage': '{:.2f}%'}))
    else:
        st.info("Your portfolio is empty. Add some stocks to get started!")

def add_stock_to_portfolio(user_id, portfolio):
    st.header("Add Stock to Portfolio")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        new_stock = st.text_input("Enter stock ticker:")
    with col2:
        new_quantity = st.number_input("Enter quantity:", min_value=1, step=1)
    with col3:
        if st.button("Add to Portfolio"):
            if new_stock in portfolio:
                portfolio[new_stock] += new_quantity
            else:
                portfolio[new_stock] = new_quantity
            user_data = load_user_data(user_id)
            user_data["portfolio"] = portfolio
            save_user_data(user_id, user_data)
            st.success(f"Added {new_quantity} shares of {new_stock} to your portfolio.")

def perform_portfolio_analysis(portfolio_returns):
    st.header("Portfolio Analysis")
    
    metrics = calculate_portfolio_metrics(portfolio_returns)
    
    col1, col2 = st.columns(2)
    with col1:
        display_portfolio_metrics(metrics)
    with col2:
        plot_portfolio_returns(portfolio_returns.index, portfolio_returns)

def calculate_portfolio_metrics(returns):
    if len(returns) < 2:
        return {
            'return': np.nan,
            'volatility': np.nan,
            'sharpe_ratio': np.nan,
            'skewness': np.nan,
            'kurtosis': np.nan,
            'shapiro_p_value': np.nan,
            'cumulative_return': np.nan,
            'var_95': np.nan,
            'cvar_95': np.nan
        }

    portfolio_return = np.mean(returns) * 252  # Annualized return
    portfolio_volatility = np.std(returns) * np.sqrt(252)  # Annualized volatility
    sharpe_ratio = portfolio_return / portfolio_volatility
    skewness = stats.skew(returns)
    kurtosis = stats.kurtosis(returns)
    _, p_value = stats.shapiro(returns)
    cumulative_return = (1 + returns).prod() - 1
    var_95 = np.percentile(returns, 5)
    cvar_95 = returns[returns <= var_95].mean()
    
    return {
        'return': portfolio_return,
        'volatility': portfolio_volatility,
        'sharpe_ratio': sharpe_ratio,
        'skewness': skewness,
        'kurtosis': kurtosis,
        'shapiro_p_value': p_value,
        'cumulative_return': cumulative_return,
        'var_95': var_95,
        'cvar_95': cvar_95
    }

def display_portfolio_metrics(metrics):
    st.subheader("Portfolio Metrics")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Annual Return", f"{metrics['return']:.2%}" if not np.isnan(metrics['return']) else "N/A")
        st.metric("Annual Volatility", f"{metrics['volatility']:.2%}" if not np.isnan(metrics['volatility']) else "N/A")
        st.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}" if not np.isnan(metrics['sharpe_ratio']) else "N/A")
        st.metric("Skewness", f"{metrics['skewness']:.2f}" if not np.isnan(metrics['skewness']) else "N/A")
        st.metric("Kurtosis", f"{metrics['kurtosis']:.2f}" if not np.isnan(metrics['kurtosis']) else "N/A")
    with col2:
        st.metric("Shapiro-Wilk p-value", f"{metrics['shapiro_p_value']:.4f}" if not np.isnan(metrics['shapiro_p_value']) else "N/A")
        st.metric("Cumulative Return", f"{metrics['cumulative_return']:.2%}" if not np.isnan(metrics['cumulative_return']) else "N/A")
        st.metric("Value at Risk (95%)", f"{metrics['var_95']:.2%}" if not np.isnan(metrics['var_95']) else "N/A")
        st.metric("Conditional VaR (95%)", f"{metrics['cvar_95']:.2%}" if not np.isnan(metrics['cvar_95']) else "N/A")
    
    with st.expander("Metrics Explanation"):
        st.write("""
        - **Annual Return**: The expected yearly return of the portfolio.
        - **Annual Volatility**: The amount of risk or fluctuation in the portfolio returns.
        - **Sharpe Ratio**: Measures the risk-adjusted return. Higher is better.
        - **Skewness**: Measures the asymmetry of returns. Positive skewness is generally preferred.
        - **Kurtosis**: Measures the tailedness of the return distribution. Higher kurtosis indicates more extreme outcomes.
        - **Shapiro-Wilk p-value**: Tests for normality of returns. A p-value > 0.05 suggests normally distributed returns.
        - **Cumulative Return**: The total return over the period.
        - **Value at Risk (95%)**: The maximum loss expected with 95% confidence over a day.
        - **Conditional VaR (95%)**: The expected loss when the loss exceeds the VaR.
        """)

def plot_portfolio_returns(dates, returns):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=returns, mode='lines', name='Daily Returns'))
    fig.add_trace(go.Scatter(x=dates, y=returns.cumsum(), mode='lines', name='Cumulative Returns'))
    fig.update_layout(title='Portfolio Returns Over Time', xaxis_title='Date', yaxis_title='Returns')
    st.plotly_chart(fig, use_container_width=True)

def portfolio_return(weights, returns):
    return np.sum(returns.mean() * weights) * 252

def portfolio_volatility(weights, cov_matrix):
    return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(252)

def negative_sharpe_ratio(weights, returns, cov_matrix, risk_free_rate):
    p_return = portfolio_return(weights, returns)
    p_volatility = portfolio_volatility(weights, cov_matrix)
    return -(p_return - risk_free_rate) / p_volatility

def perform_portfolio_optimization(returns, portfolio):
    st.header("Portfolio Optimization")
    
    if len(portfolio) < 2:
        st.warning("Portfolio optimization requires at least two stocks. Add more stocks to optimize your portfolio.")
        return
    
    risk_free_rate = st.number_input("Enter risk-free rate:", min_value=0.0, max_value=1.0, value=0.02, step=0.001)
    
    cov_matrix = returns.cov()
    
    # Maximum Sharpe Ratio Portfolio
    msr_weights = maximize_sharpe_ratio(returns, cov_matrix, risk_free_rate)
    
    # Global Minimum Variance Portfolio
    gmv_weights = global_minimum_variance(cov_matrix)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Maximized Sharpe Ratio Portfolio")
        display_optimal_portfolio(msr_weights, returns, cov_matrix, risk_free_rate)
    
    with col2:
        st.subheader("Global Minimum Variance Portfolio")
        display_optimal_portfolio(gmv_weights, returns, cov_matrix, risk_free_rate)

def maximize_sharpe_ratio(returns, cov_matrix, risk_free_rate):
    num_stocks = len(returns.columns)
    initial_guess = num_stocks * [1. / num_stocks, ]
    bounds = tuple((0, 1) for _ in range(num_stocks))
    constraints = {'type': 'eq', 'fun': lambda weights: np.sum(weights) - 1}
    
    result = minimize(negative_sharpe_ratio, initial_guess, args=(returns, cov_matrix, risk_free_rate), 
                      method='SLSQP', bounds=bounds, constraints=constraints)
    return result.x

def global_minimum_variance(cov_matrix):
    num_stocks = len(cov_matrix)
    initial_guess = num_stocks * [1. / num_stocks, ]
    bounds = tuple((0, 1) for _ in range(num_stocks))
    constraints = {'type': 'eq', 'fun': lambda weights: np.sum(weights) - 1}
    
    def portfolio_vol(weights):
        return portfolio_volatility(weights, cov_matrix)
    
    result = minimize(portfolio_vol, initial_guess, bounds=bounds, constraints=constraints)
    return result.x

def display_optimal_portfolio(weights, returns, cov_matrix, risk_free_rate):
    p_return = portfolio_return(weights, returns)
    p_volatility = portfolio_volatility(weights, cov_matrix)
    sharpe_ratio = (p_return - risk_free_rate) / p_volatility
    
    st.metric("Expected Annual Return", f"{p_return:.2%}")
    st.metric("Expected Annual Volatility", f"{p_volatility:.2%}")
    st.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")
    
    df = pd.DataFrame({'Stock': returns.columns, 'Weight': weights})
    fig = go.Figure(data=[go.Pie(labels=df['Stock'], values=df['Weight'], hole=.3)])
    fig.update_layout(title='Optimal Portfolio Composition')
    st.plotly_chart(fig, use_container_width=True)

def perform_monte_carlo_var(returns, portfolio):
    st.header("Monte Carlo VaR Simulation")
    
    if len(portfolio) < 2:
        st.warning("Monte Carlo VaR simulation requires at least two stocks. Add more stocks to run the simulation.")
        return
    
    iterations = st.slider("Number of iterations", 1000, 100000, 10000, step=1000)
    
    portfolio_return = np.mean(returns, axis=1)
    portfolio_volatility = np.std(returns, axis=1)
    
    simulations = np.random.normal(portfolio_return.mean(), portfolio_volatility.mean(), (iterations, len(returns)))
    simulated_returns = np.exp(simulations.cumsum(axis=1))
    
    var_95 = np.percentile(simulated_returns[:, -1], 5)
    cvar_95 = simulated_returns[simulated_returns[:, -1] <= var_95].mean()
    
    st.metric("Value at Risk (95%)", f"{var_95:.2%}")
    st.metric("Conditional VaR (95%)", f"{cvar_95:.2%}")
    
    st.subheader("Monte Carlo Simulation Distribution")
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=simulated_returns[:, -1], nbinsx=50))
    fig.update_layout(title='Distribution of Simulated Portfolio Values', xaxis_title='Portfolio Value', yaxis_title='Frequency')
    st.plotly_chart(fig, use_container_width=True)

def portfolio_management_interface(user_id):
    try:
        st.title('📊 Advanced Portfolio Management')
        
        user_data = load_user_data(user_id)
        portfolio = user_data.get("portfolio", {})
        
        display_current_portfolio(portfolio)
        add_stock_to_portfolio(user_id, portfolio)
        
        if portfolio:
            # Fetch historical data
            tickers = list(portfolio.keys())
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            try:
                data = yf.download(tickers, start=start_date, end=end_date)['Adj Close']
                # Handle cases where there might be only one stock in the portfolio
                if len(tickers) == 1:
                    data = data.to_frame()  # Ensure data is in DataFrame format
                elif len(tickers) == 2:
                    data = data.fillna(method='pad')  # Fill missing data
                    
                # Calculate returns
                returns = data.pct_change().dropna()
                
                # Calculate portfolio metrics
                weights = np.array([portfolio[ticker] for ticker in tickers])
                weights = weights / np.sum(weights)
                
                # Check for dimensionality issues
                if len(weights) == 1:
                    portfolio_returns = returns * weights[0]
                else:
                    portfolio_returns = returns.dot(weights)
                
                st.sidebar.title("Navigation")
                analysis_options = ["Portfolio Overview", "Portfolio Analysis", "Portfolio Optimization", "Monte Carlo Simulation"]
                selected_analysis = st.sidebar.radio("Choose Analysis", analysis_options)
                
                if selected_analysis == "Portfolio Overview":
                    perform_portfolio_overview(portfolio_returns, returns, portfolio)
                elif selected_analysis == "Portfolio Analysis":
                    perform_portfolio_analysis(portfolio_returns)
                elif selected_analysis == "Portfolio Optimization":
                    perform_portfolio_optimization(returns, portfolio)
                elif selected_analysis == "Monte Carlo Simulation":
                    perform_monte_carlo_var(returns, portfolio)
            except Exception as e:
                st.error(f"An error occurred while processing your portfolio: {e}")
        else:
            st.info("Your portfolio is empty. Add some stocks to get started!")

    except Exception as e:
        pass