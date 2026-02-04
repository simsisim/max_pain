"""
Report Generator - Creates output reports in multiple formats
"""

import logging
import json
import csv
from datetime import datetime
from jinja2 import Template
import os


class ReportGenerator:
    """
    Generates max pain reports in multiple formats (HTML, CSV, JSON)
    """

    def __init__(self, config):
        self.logger = logging.getLogger('max_pain.report_generator')
        self.config = config
        self.output_dir = config.get('OUTPUT', 'output_dir', fallback='results')
        self.highlight_top_n = config.getint('OUTPUT', 'highlight_top_n', fallback=20)

    def generate_reports(self, results_list, output_formats=None):
        """
        Generate reports in specified formats

        Args:
            results_list: List of calculation results (dicts)
            output_formats: List of formats to generate (html, csv, json)

        Returns:
            dict with paths to generated files
        """
        if output_formats is None:
            formats_str = self.config.get('OUTPUT', 'output_formats', fallback='html,csv,json')
            output_formats = [f.strip() for f in formats_str.split(',')]

        self.logger.info(f"Generating reports in formats: {', '.join(output_formats)}")

        generated_files = {}

        # Sort results
        sort_by = self.config.get('OUTPUT', 'sort_by', fallback='net_premium')
        results_list = self._sort_results(results_list, sort_by)

        # Mark top N
        results_list = self._mark_top_n(results_list)

        # Generate each format
        if 'csv' in output_formats:
            csv_path = self.generate_csv_report(results_list)
            generated_files['csv'] = csv_path

        if 'json' in output_formats:
            json_path = self.generate_json_report(results_list)
            generated_files['json'] = json_path

        if 'html' in output_formats:
            html_path = self.generate_html_report(results_list)
            generated_files['html'] = html_path

        return generated_files

    def _sort_results(self, results_list, sort_by='net_premium'):
        """
        Sort results by specified key

        Args:
            results_list: List of results
            sort_by: Key to sort by (net_premium, ticker, pct_change)

        Returns:
            Sorted list
        """
        if sort_by == 'net_premium':
            # Sort by absolute value of net premium (descending)
            return sorted(results_list, key=lambda x: abs(x.get('net_call_put_premium', 0)), reverse=True)
        elif sort_by == 'ticker':
            return sorted(results_list, key=lambda x: x.get('ticker', ''))
        elif sort_by == 'pct_change':
            return sorted(results_list, key=lambda x: x.get('pct_change', 0))
        else:
            return results_list

    def _mark_top_n(self, results_list):
        """
        Mark top N results by net premium

        Args:
            results_list: Sorted list of results

        Returns:
            List with is_top_n flag added
        """
        for i, result in enumerate(results_list):
            result['is_top_n'] = (i < self.highlight_top_n)
        return results_list

    def generate_csv_report(self, results_list):
        """
        Generate CSV report

        Args:
            results_list: List of calculation results

        Returns:
            Path to generated CSV file
        """
        self.logger.info("Generating CSV report")

        # Create output directory
        csv_dir = os.path.join(self.output_dir, 'csv')
        os.makedirs(csv_dir, exist_ok=True)

        # Generate filename
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"{date_str}_max_pain_report.csv"
        filepath = os.path.join(csv_dir, filename)

        # Write CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'Ticker',
                'Friday Close',
                'Max Pain',
                '% Change',
                'Net Call/(Put) Premium'
            ])

            # Data rows
            for result in results_list:
                writer.writerow([
                    result.get('ticker', ''),
                    f"{result.get('current_price', 0):.2f}",
                    f"{result.get('max_pain_price', 0):.2f}",
                    f"{result.get('pct_change', 0):+.2f}%",
                    f"{result.get('net_call_put_premium', 0):,.2f}"
                ])

        self.logger.info(f"CSV report saved to: {filepath}")
        return filepath

    def generate_json_report(self, results_list):
        """
        Generate JSON report

        Args:
            results_list: List of calculation results

        Returns:
            Path to generated JSON file
        """
        self.logger.info("Generating JSON report")

        # Create output directory
        json_dir = os.path.join(self.output_dir, 'json')
        os.makedirs(json_dir, exist_ok=True)

        # Generate filename
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"{date_str}_max_pain_results.json"
        filepath = os.path.join(json_dir, filename)

        # Calculate summary stats
        summary = self._calculate_summary(results_list)

        # Create report structure
        report = {
            'metadata': {
                'report_date': date_str,
                'generation_timestamp': datetime.now().isoformat(),
                'data_source': self.config.get('DATA_SOURCE', 'source', fallback='CBOE'),
                'ticker_count': len(results_list),
                'top_n_highlighted': self.highlight_top_n
            },
            'results': results_list,
            'summary': summary
        }

        # Write JSON
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"JSON report saved to: {filepath}")
        return filepath

    def generate_html_report(self, results_list):
        """
        Generate HTML report

        Args:
            results_list: List of calculation results

        Returns:
            Path to generated HTML file
        """
        self.logger.info("Generating HTML report")

        # Create output directory
        html_dir = os.path.join(self.output_dir, 'html')
        os.makedirs(html_dir, exist_ok=True)

        # Load template
        template_path = 'templates/max_pain_report.html'
        if not os.path.exists(template_path):
            self.logger.warning(f"Template not found: {template_path}, using default")
            template_content = self._get_default_template()
        else:
            with open(template_path, 'r') as f:
                template_content = f.read()

        template = Template(template_content)

        # Prepare data
        date_str = datetime.now().strftime('%Y-%m-%d')
        summary = self._calculate_summary(results_list)

        # Render template
        html_content = template.render(
            report_date=date_str,
            generation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            results=results_list,
            summary=summary,
            ticker_count=len(results_list),
            data_source=self.config.get('DATA_SOURCE', 'source', fallback='CBOE')
        )

        # Save HTML
        filename = f"{date_str}_max_pain_report.html"
        filepath = os.path.join(html_dir, filename)

        with open(filepath, 'w') as f:
            f.write(html_content)

        self.logger.info(f"HTML report saved to: {filepath}")
        return filepath

    def _calculate_summary(self, results_list):
        """
        Calculate summary statistics

        Args:
            results_list: List of results

        Returns:
            dict with summary stats
        """
        if not results_list:
            return {}

        total_net_premium = sum(r.get('net_call_put_premium', 0) for r in results_list)
        avg_pct_change = sum(r.get('pct_change', 0) for r in results_list) / len(results_list)
        bearish_count = sum(1 for r in results_list if r.get('pct_change', 0) < 0)
        bullish_count = sum(1 for r in results_list if r.get('pct_change', 0) > 0)

        return {
            'total_net_premium': total_net_premium,
            'avg_pct_change': avg_pct_change,
            'bearish_count': bearish_count,
            'bullish_count': bullish_count,
            'neutral_count': len(results_list) - bearish_count - bullish_count
        }

    def _get_default_template(self):
        """
        Get default HTML template if file not found

        Returns:
            HTML template string
        """
        return """<!DOCTYPE html>
<html>
<head>
    <title>Max Pain Report - {{ report_date }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 10px;
        }
        h2 {
            color: #34495e;
            text-align: center;
            font-weight: normal;
            margin-top: 0;
        }
        .disclaimer {
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th {
            background-color: #34495e;
            color: white;
            padding: 12px;
            text-align: left;
        }
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .highlight {
            background-color: #e8f4f8;
            font-weight: bold;
        }
        .negative {
            color: #c0392b;
        }
        .positive {
            color: #27ae60;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            color: #7f8c8d;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>MAX PAIN REPORT</h1>
        <h2>{{ report_date }}</h2>

        <div class="disclaimer">
            <strong>Disclaimer:</strong> Max pain is not a guarantee and is intended to be used solely for directional clues.
            All values below are computed using the data provided by {{ data_source }}.
            We cannot attest to the accuracy of the data. Trade at your own risk.
        </div>

        <p><strong>Total Tickers:</strong> {{ ticker_count }}</p>
        <p><strong>Bearish Bias:</strong> {{ summary.bearish_count }} | <strong>Bullish Bias:</strong> {{ summary.bullish_count }}</p>

        <h3>Sorted by Net Premium</h3>
        <table>
            <thead>
                <tr>
                    <th>Ticker</th>
                    <th>Friday Close</th>
                    <th>Max Pain</th>
                    <th>% Change</th>
                    <th>Net Call/(Put) Premium</th>
                </tr>
            </thead>
            <tbody>
                {% for result in results %}
                <tr {% if result.is_top_n %}class="highlight"{% endif %}>
                    <td>{{ result.ticker }}{% if result.is_top_n %}*{% endif %}</td>
                    <td>${{ "%.2f"|format(result.current_price) }}</td>
                    <td>${{ "%.2f"|format(result.max_pain_price) }}</td>
                    <td class="{% if result.pct_change < 0 %}negative{% else %}positive{% endif %}">
                        {{ "%+.2f"|format(result.pct_change) }}%
                    </td>
                    <td>${{ "{:,.2f}".format(result.net_call_put_premium) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div class="footer">
            <p>Generated with Max Pain Calculator v1.0</p>
            <p>Generated: {{ generation_time }}</p>
            <p>*An asterisk indicates a stock ranking in the top {{ summary.bearish_count + summary.bullish_count }} in terms of net premium (absolute value).</p>
        </div>
    </div>
</body>
</html>"""
