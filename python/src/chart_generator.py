"""
Max Pain Chart Generator

Generates visualization charts for max pain analysis using matplotlib.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import logging


class MaxPainChartGenerator:
    """
    Generates PNG charts for max pain visualization
    
    Supports multiple chart types:
    - total_payout: Shows total payout curve with max pain marker
    - open_interest: Shows call/put OI distribution
    - pain_comparison: Shows call vs put pain breakdown
    """
    
    def __init__(self, config):
        """
        Initialize chart generator with configuration
        
        Args:
            config: ConfigParser object
        """
        self.config = config
        self.chart_dir = config.get('OUTPUT', 'chart_dir', fallback='results/charts')
        self.dpi = config.getint('OUTPUT', 'chart_dpi', fallback=150)
        self.width = config.getint('OUTPUT', 'chart_width', fallback=12)
        self.height = config.getint('OUTPUT', 'chart_height', fallback=6)
        self.logger = logging.getLogger('max_pain.ChartGenerator')
        
        # Create chart directory
        os.makedirs(self.chart_dir, exist_ok=True)
    
    def generate_charts(self, result):
        """
        Generate all enabled chart types for a result
        
        Args:
            result: Max pain calculation result dict with option_data
        
        Returns:
            list of generated file paths
        """
        # Check if option_data is available
        if 'option_data' not in result:
            self.logger.warning(f"No option_data in result for {result.get('ticker', 'UNKNOWN')}, skipping charts")
            return []
        
        generated_files = []
        chart_types = self._get_enabled_chart_types()
        
        for chart_type in chart_types:
            try:
                filepath = self._generate_chart(chart_type, result)
                if filepath is None:
                    self.logger.info(f"Skipped {chart_type} chart (required data not available)")
                    continue
                generated_files.append(filepath)
                self.logger.info(f"Generated {chart_type} chart: {os.path.basename(filepath)}")
            except Exception as e:
                self.logger.error(f"Error generating {chart_type} chart: {e}")
        
        return generated_files
    
    def _get_enabled_chart_types(self):
        """Get list of chart types to generate from config"""
        chart_types_str = self.config.get('OUTPUT', 'chart_types', fallback='total_payout,open_interest')

        if chart_types_str.lower() == 'all':
            return ['total_payout', 'open_interest', 'pain_comparison', 'gamma_overlay']

        return [ct.strip() for ct in chart_types_str.split(',')]

    def _generate_chart(self, chart_type, result):
        """Route to appropriate chart generation method"""
        if chart_type == 'total_payout':
            return self._generate_total_payout_chart(result)
        elif chart_type == 'open_interest':
            return self._generate_open_interest_chart(result)
        elif chart_type == 'pain_comparison':
            return self._generate_pain_comparison_chart(result)
        elif chart_type == 'gamma_overlay':
            return self._generate_gamma_overlay_chart(result)
        else:
            raise ValueError(f"Unknown chart type: {chart_type}")
    
    def _generate_total_payout_chart(self, result):
        """
        Generate total payout vs strike price chart
        
        Shows the total payout curve with markers for current price and max pain
        """
        option_data = result['option_data']
        strikes = option_data['Strike'].values
        
        # Calculate total payout at each strike
        payouts = []
        for strike in strikes:
            call_payout, put_payout = self._calculate_payouts_at_strike(strike, option_data)
            payouts.append(call_payout + put_payout)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(self.width, self.height))
        
        # Plot payout curve
        ax.plot(strikes, payouts, 'b-', linewidth=2.5, label='Total Payout', zorder=3)
        
        # Fill area under curve
        ax.fill_between(strikes, payouts, alpha=0.15, color='blue', zorder=1)
        
        # Current price marker
        ax.axvline(result['current_price'], color='#2196F3', 
                   linestyle='--', linewidth=2, 
                   label=f"Current: ${result['current_price']:.2f}", zorder=4)
        
        # Max pain marker
        ax.axvline(result['max_pain_price'], color='#F44336',
                   linestyle='-', linewidth=3,
                   label=f"Max Pain: ${result['max_pain_price']:.2f}", zorder=5)
        
        # Shaded region between current and max pain
        if result['current_price'] != result['max_pain_price']:
            ax.axvspan(result['current_price'], result['max_pain_price'],
                       alpha=0.1, color='yellow', zorder=2)
        
        # Labels and title
        ax.set_xlabel('Strike Price ($)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Total Payout ($)', fontsize=12, fontweight='bold')
        
        title = f"{result['ticker']} - Max Pain Analysis\n"
        title += f"Expiration: {result['expiration_date']} | Change: {result['pct_change']:+.2f}%"
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # Legend
        ax.legend(loc='best', fontsize=10, framealpha=0.9)
        
        # Grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        
        # Format y-axis as currency
        def currency_formatter(x, p):
            if abs(x) >= 1e9:
                return f'${x/1e9:.1f}B'
            elif abs(x) >= 1e6:
                return f'${x/1e6:.1f}M'
            elif abs(x) >= 1e3:
                return f'${x/1e3:.1f}K'
            else:
                return f'${x:.0f}'
        
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(currency_formatter))
        
        plt.tight_layout()
        
        # Save
        exp_str = result['expiration_date'].replace('-', '')
        filename = f"{result['ticker']}_{exp_str}_total_payout.png"
        filepath = os.path.join(self.chart_dir, filename)
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def _generate_open_interest_chart(self, result):
        """
        Generate open interest distribution chart
        
        Shows call and put OI as bars with price markers
        """
        option_data = result['option_data']
        strikes = option_data['Strike'].values
        call_oi = option_data['Call_OI'].values
        put_oi = option_data['Put_OI'].values
        
        # Create figure
        fig, ax = plt.subplots(figsize=(self.width, self.height))
        
        # Calculate bar width
        if len(strikes) > 1:
            width = (strikes[1] - strikes[0]) * 0.35
        else:
            width = 1.0
        
        # Plot bars
        ax.bar(strikes - width/2, call_oi, width,
               label='Call OI', color='#4CAF50', alpha=0.7, edgecolor='darkgreen')
        ax.bar(strikes + width/2, put_oi, width,
               label='Put OI', color='#F44336', alpha=0.7, edgecolor='darkred')
        
        # Price markers
        ax.axvline(result['current_price'], color='#2196F3',
                   linestyle='--', linewidth=2,
                   label=f"Current: ${result['current_price']:.2f}", zorder=10)
        ax.axvline(result['max_pain_price'], color='#FF6F00',
                   linestyle='-', linewidth=3,
                   label=f"Max Pain: ${result['max_pain_price']:.2f}", zorder=10)
        
        # Labels and title
        ax.set_xlabel('Strike Price ($)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Open Interest (Contracts)', fontsize=12, fontweight='bold')
        
        title = f"{result['ticker']} - Open Interest Distribution\n"
        title += f"Expiration: {result['expiration_date']}"
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # Legend
        ax.legend(loc='best', fontsize=10, framealpha=0.9)
        
        # Grid (y-axis only)
        ax.grid(True, alpha=0.3, axis='y', linestyle='--', linewidth=0.5)
        
        # Format y-axis with commas
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{int(x):,}'))
        
        plt.tight_layout()
        
        # Save
        exp_str = result['expiration_date'].replace('-', '')
        filename = f"{result['ticker']}_{exp_str}_open_interest.png"
        filepath = os.path.join(self.chart_dir, filename)
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def _generate_pain_comparison_chart(self, result):
        """
        Generate call vs put pain comparison chart
        
        Shows breakdown of how calls and puts contribute to total pain
        """
        option_data = result['option_data']
        strikes = option_data['Strike'].values
        
        # Calculate call and put payouts separately
        call_payouts = []
        put_payouts = []
        
        for strike in strikes:
            call_payout, put_payout = self._calculate_payouts_at_strike(strike, option_data)
            call_payouts.append(call_payout)
            put_payouts.append(put_payout)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(self.width, self.height))
        
        # Stacked area plot
        ax.fill_between(strikes, 0, call_payouts, 
                        label='Call Payout', color='#4CAF50', alpha=0.6)
        ax.fill_between(strikes, call_payouts, 
                        np.array(call_payouts) + np.array(put_payouts),
                        label='Put Payout', color='#F44336', alpha=0.6)
        
        # Total line
        total_payouts = np.array(call_payouts) + np.array(put_payouts)
        ax.plot(strikes, total_payouts, 'k-', linewidth=2, label='Total')
        
        # Price markers
        ax.axvline(result['current_price'], color='blue',
                   linestyle='--', linewidth=2, label='Current Price')
        ax.axvline(result['max_pain_price'], color='red',
                   linestyle='-', linewidth=3, label='Max Pain')
        
        # Labels
        ax.set_xlabel('Strike Price ($)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Payout ($)', fontsize=12, fontweight='bold')
        ax.set_title(f"{result['ticker']} - Call vs Put Pain Comparison", 
                     fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        
        # Save
        exp_str = result['expiration_date'].replace('-', '')
        filename = f"{result['ticker']}_{exp_str}_pain_comparison.png"
        filepath = os.path.join(self.chart_dir, filename)
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def _generate_gamma_overlay_chart(self, result):
        """
        Generate net gamma overlay chart (Mod 5).

        Twin-axis chart:
          Left Y  — total payout curve (line)
          Right Y — net gamma bars per strike (green = call-dominated, red = put-dominated)

        Vertical lines: current price (blue dashed), max pain (red solid).

        Returns None (with a warning logged) if net_gamma_data is not in the result.
        """
        if 'net_gamma_data' not in result:
            self.logger.warning(
                f"No net_gamma_data for {result.get('ticker', 'UNKNOWN')} — "
                "gamma_overlay chart requires YF gamma columns; skipping."
            )
            return None

        option_data = result['option_data']
        net_gamma = result['net_gamma_data']  # Series indexed by Strike
        strikes = option_data['Strike'].values

        # Total payout at each strike (left axis)
        payouts = []
        for strike in strikes:
            call_payout, put_payout = self._calculate_payouts_at_strike(strike, option_data)
            payouts.append(call_payout + put_payout)

        fig, ax1 = plt.subplots(figsize=(self.width, self.height))

        # Left axis: total payout curve
        ax1.plot(strikes, payouts, 'b-', linewidth=2.5, label='Total Payout', zorder=3)
        ax1.fill_between(strikes, payouts, alpha=0.1, color='blue', zorder=1)
        ax1.set_xlabel('Strike Price ($)', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Total Payout ($)', color='steelblue', fontsize=11)
        ax1.tick_params(axis='y', labelcolor='steelblue')

        def currency_formatter(x, p):
            if abs(x) >= 1e9:
                return f'${x/1e9:.1f}B'
            elif abs(x) >= 1e6:
                return f'${x/1e6:.1f}M'
            elif abs(x) >= 1e3:
                return f'${x/1e3:.1f}K'
            else:
                return f'${x:.0f}'

        ax1.yaxis.set_major_formatter(ticker.FuncFormatter(currency_formatter))

        # Right axis: net gamma bars
        ax2 = ax1.twinx()
        gamma_strikes = net_gamma.index.values
        gamma_values = net_gamma.values
        bar_colors = ['#4CAF50' if v >= 0 else '#F44336' for v in gamma_values]

        bar_width = (
            (gamma_strikes[1] - gamma_strikes[0]) * 0.6
            if len(gamma_strikes) > 1
            else 1.0
        )
        ax2.bar(
            gamma_strikes, gamma_values,
            width=bar_width, color=bar_colors, alpha=0.55,
            label='Net Gamma', zorder=2
        )
        ax2.axhline(0, color='gray', linewidth=0.7, linestyle=':', zorder=1)
        ax2.set_ylabel('Net Gamma (Call − Put)', color='gray', fontsize=11)
        ax2.tick_params(axis='y', labelcolor='gray')

        # Price markers (drawn on ax1 so they appear above bars)
        ax1.axvline(
            result['current_price'], color='#2196F3',
            linestyle='--', linewidth=2,
            label=f"Current: ${result['current_price']:.2f}", zorder=5
        )
        ax1.axvline(
            result['max_pain_price'], color='#F44336',
            linestyle='-', linewidth=3,
            label=f"Max Pain: ${result['max_pain_price']:.2f}", zorder=6
        )

        # Combined legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2,
                   loc='best', fontsize=10, framealpha=0.9)

        title = f"{result['ticker']} - Net Gamma Overlay\n"
        title += f"Expiration: {result['expiration_date']} | Change: {result['pct_change']:+.2f}%"
        ax1.set_title(title, fontsize=14, fontweight='bold', pad=20)

        ax1.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

        plt.tight_layout()

        exp_str = result['expiration_date'].replace('-', '')
        filename = f"{result['ticker']}_{exp_str}_gamma_overlay.png"
        filepath = os.path.join(self.chart_dir, filename)
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        plt.close()

        return filepath

    def _calculate_payouts_at_strike(self, strike_price, option_data):
        """
        Calculate call and put payouts at a given strike price
        
        Args:
            strike_price: Price to calculate payout at
            option_data: DataFrame with Strike, Call_OI, Put_OI
        
        Returns:
            tuple: (call_payout, put_payout)
        """
        call_payout = 0
        put_payout = 0
        
        for _, row in option_data.iterrows():
            strike = row['Strike']
            call_oi = row['Call_OI']
            put_oi = row['Put_OI']
            
            # Call payout: max(0, stock_price - strike) * OI * 100
            if strike_price > strike:
                call_payout += (strike_price - strike) * call_oi * 100
            
            # Put payout: max(0, strike - stock_price) * OI * 100
            if strike_price < strike:
                put_payout += (strike - strike_price) * put_oi * 100
        
        return call_payout, put_payout
