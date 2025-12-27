"""
Phase 3: High Availability Rendering Service
Visualization Script - Generate graphs from performance data

This script creates the required performance graphs:
1. Latency vs Time
2. Throughput vs Time
3. Annotated failure/recovery points
"""

import os
import sys
import json
import argparse
import csv
from datetime import datetime

# Try to import matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available. Install with: pip install matplotlib")


def load_time_series(csv_path: str) -> dict:
    """Load time series data from CSV."""
    data = {
        'time': [],
        'request_count': [],
        'success_count': [],
        'failure_count': [],
        'avg_latency_ms': [],
        'p95_latency_ms': [],
        'throughput_rps': []
    }
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data['time'].append(float(row['time']))
            data['request_count'].append(int(row['request_count']))
            data['success_count'].append(int(row['success_count']))
            data['failure_count'].append(int(row['failure_count']))
            data['avg_latency_ms'].append(float(row['avg_latency_ms']))
            data['p95_latency_ms'].append(float(row['p95_latency_ms']))
            data['throughput_rps'].append(float(row['throughput_rps']))
    
    return data


def load_failure_events(csv_path: str) -> list:
    """Load failure events from CSV."""
    events = []
    
    if not os.path.exists(csv_path):
        return events
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            events.append({
                'elapsed_time': float(row['elapsed_time']),
                'event_type': row['event_type'],
                'replica_id': row['replica_id'],
                'recovery_time': float(row.get('recovery_time', 0))
            })
    
    return events


def generate_latency_graph(data: dict, events: list, output_path: str):
    """Generate Latency vs Time graph."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot latency lines
    ax.plot(data['time'], data['avg_latency_ms'], 
            label='Average Latency', color='blue', linewidth=2)
    ax.plot(data['time'], data['p95_latency_ms'], 
            label='P95 Latency', color='orange', linewidth=2, linestyle='--')
    
    # Annotate failure events
    for event in events:
        if event['event_type'] in ['SERVICE_CRASH', 'FAULT_INJECTION']:
            ax.axvline(x=event['elapsed_time'], color='red', 
                      linestyle=':', alpha=0.7, linewidth=2)
            ax.annotate(f"Failure\n({event['replica_id']})", 
                       xy=(event['elapsed_time'], ax.get_ylim()[1] * 0.9),
                       fontsize=9, ha='center', color='red')
        elif event['event_type'] == 'RECOVERED':
            ax.axvline(x=event['elapsed_time'], color='green', 
                      linestyle=':', alpha=0.7, linewidth=2)
            ax.annotate(f"Recovery\n({event['recovery_time']:.1f}s)", 
                       xy=(event['elapsed_time'], ax.get_ylim()[1] * 0.7),
                       fontsize=9, ha='center', color='green')
    
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Latency (ms)', fontsize=12)
    ax.set_title('Latency vs Time - Fault Tolerance Demo', fontsize=14)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # Add legend for fault annotations
    failure_patch = mpatches.Patch(color='red', alpha=0.3, label='Failure Event')
    recovery_patch = mpatches.Patch(color='green', alpha=0.3, label='Recovery')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    
    print(f"Latency graph saved to: {output_path}")


def generate_throughput_graph(data: dict, events: list, output_path: str):
    """Generate Throughput vs Time graph."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot throughput
    ax.fill_between(data['time'], data['throughput_rps'], 
                   alpha=0.3, color='blue')
    ax.plot(data['time'], data['throughput_rps'], 
            label='Throughput', color='blue', linewidth=2)
    
    # Annotate failure events
    for event in events:
        if event['event_type'] in ['SERVICE_CRASH', 'FAULT_INJECTION']:
            ax.axvline(x=event['elapsed_time'], color='red', 
                      linestyle=':', alpha=0.7, linewidth=2)
            ax.annotate(f"Failure", 
                       xy=(event['elapsed_time'], ax.get_ylim()[1] * 0.9),
                       fontsize=9, ha='center', color='red')
        elif event['event_type'] == 'RECOVERED':
            ax.axvline(x=event['elapsed_time'], color='green', 
                      linestyle=':', alpha=0.7, linewidth=2)
    
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Throughput (requests/second)', fontsize=12)
    ax.set_title('Throughput vs Time - Fault Tolerance Demo', fontsize=14)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    
    print(f"Throughput graph saved to: {output_path}")


def generate_combined_graph(data: dict, events: list, output_path: str):
    """Generate combined Latency and Throughput graph."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    # Latency subplot
    ax1.plot(data['time'], data['avg_latency_ms'], 
             label='Average Latency', color='blue', linewidth=2)
    ax1.plot(data['time'], data['p95_latency_ms'], 
             label='P95 Latency', color='orange', linewidth=2, linestyle='--')
    
    for event in events:
        if event['event_type'] in ['SERVICE_CRASH', 'FAULT_INJECTION']:
            ax1.axvspan(event['elapsed_time'], 
                       event['elapsed_time'] + event.get('recovery_time', 2),
                       alpha=0.2, color='red')
            ax1.axvline(x=event['elapsed_time'], color='red', 
                       linestyle=':', alpha=0.7, linewidth=2)
    
    ax1.set_ylabel('Latency (ms)', fontsize=12)
    ax1.set_title('Performance During Fault Injection', fontsize=14)
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # Throughput subplot
    ax2.fill_between(data['time'], data['throughput_rps'], 
                    alpha=0.3, color='green')
    ax2.plot(data['time'], data['throughput_rps'], 
             label='Throughput', color='green', linewidth=2)
    
    for event in events:
        if event['event_type'] in ['SERVICE_CRASH', 'FAULT_INJECTION']:
            ax2.axvspan(event['elapsed_time'], 
                       event['elapsed_time'] + event.get('recovery_time', 2),
                       alpha=0.2, color='red')
            ax2.axvline(x=event['elapsed_time'], color='red', 
                       linestyle=':', alpha=0.7, linewidth=2)
    
    ax2.set_xlabel('Time (seconds)', fontsize=12)
    ax2.set_ylabel('Throughput (req/s)', fontsize=12)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    
    # Add failure/recovery legend
    failure_patch = mpatches.Patch(color='red', alpha=0.2, label='Failure Period')
    fig.legend(handles=[failure_patch], loc='upper center', ncol=1, 
              bbox_to_anchor=(0.5, 0.02))
    
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.08)
    plt.savefig(output_path, dpi=150)
    plt.close()
    
    print(f"Combined graph saved to: {output_path}")


def generate_success_rate_graph(data: dict, events: list, output_path: str):
    """Generate success rate over time."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Calculate success rate
    success_rates = []
    for i in range(len(data['time'])):
        total = data['request_count'][i]
        success = data['success_count'][i]
        rate = (success / total * 100) if total > 0 else 100
        success_rates.append(rate)
    
    ax.fill_between(data['time'], success_rates, alpha=0.3, color='green')
    ax.plot(data['time'], success_rates, color='green', linewidth=2)
    
    # Annotate failures
    for event in events:
        if event['event_type'] in ['SERVICE_CRASH', 'FAULT_INJECTION']:
            ax.axvline(x=event['elapsed_time'], color='red', 
                      linestyle=':', alpha=0.7, linewidth=2)
    
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Success Rate (%)', fontsize=12)
    ax.set_title('Request Success Rate Over Time', fontsize=14)
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    
    print(f"Success rate graph saved to: {output_path}")


def main():
    """Generate all graphs from demo output."""
    parser = argparse.ArgumentParser(description='Generate performance graphs')
    parser.add_argument('--input-dir', type=str, default='./demo_output',
                       help='Input directory with CSV files')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Output directory for graphs (default: same as input)')
    
    args = parser.parse_args()
    
    if not MATPLOTLIB_AVAILABLE:
        print("Error: matplotlib is required for graph generation")
        print("Install with: pip install matplotlib")
        sys.exit(1)
    
    input_dir = args.input_dir
    output_dir = args.output_dir or input_dir
    
    # Check for required files
    time_series_path = os.path.join(input_dir, 'time_series.csv')
    events_path = os.path.join(input_dir, 'failure_events.csv')
    
    if not os.path.exists(time_series_path):
        print(f"Error: Time series file not found: {time_series_path}")
        print("Run the demo first: python demo.py")
        sys.exit(1)
    
    # Load data
    print(f"Loading data from {input_dir}...")
    data = load_time_series(time_series_path)
    events = load_failure_events(events_path)
    
    print(f"Loaded {len(data['time'])} data points and {len(events)} events")
    
    # Generate graphs
    os.makedirs(output_dir, exist_ok=True)
    
    print("\nGenerating graphs...")
    generate_latency_graph(data, events, 
                          os.path.join(output_dir, 'latency_graph.png'))
    generate_throughput_graph(data, events, 
                             os.path.join(output_dir, 'throughput_graph.png'))
    generate_combined_graph(data, events, 
                           os.path.join(output_dir, 'combined_graph.png'))
    generate_success_rate_graph(data, events, 
                               os.path.join(output_dir, 'success_rate_graph.png'))
    
    print(f"\nAll graphs saved to: {output_dir}")
    print("\nGenerated files:")
    print("  - latency_graph.png     (Latency vs Time)")
    print("  - throughput_graph.png  (Throughput vs Time)")
    print("  - combined_graph.png    (Both metrics combined)")
    print("  - success_rate_graph.png (Success rate over time)")


if __name__ == '__main__':
    main()
