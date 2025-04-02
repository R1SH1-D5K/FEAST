import logging
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import re
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FeedbackAnalyzer:
    """Analyze user feedback to improve the chatbot"""
    
    def __init__(self):
        self.feedback_data = []
        self.load_feedback()
    
    def load_feedback(self):
        """Load feedback data from file"""
        try:
            if os.path.exists("data/feedback.json"):
                with open("data/feedback.json", "r") as f:
                    self.feedback_data = json.load(f)
                logger.info(f"Loaded {len(self.feedback_data)} feedback entries")
        except Exception as e:
            logger.error(f"Error loading feedback data: {e}")
    
    def save_feedback(self):
        """Save feedback data to file"""
        try:
            os.makedirs("data", exist_ok=True)
            with open("data/feedback.json", "w") as f:
                json.dump(self.feedback_data, f)
            logger.info(f"Saved {len(self.feedback_data)} feedback entries")
        except Exception as e:
            logger.error(f"Error saving feedback data: {e}")
    
    def add_feedback(self, feedback: Dict[str, Any]):
        """Add a new feedback entry"""
        # Add timestamp if not present
        if "timestamp" not in feedback:
            feedback["timestamp"] = datetime.now().isoformat()
        
        self.feedback_data.append(feedback)
        self.save_feedback()
    
    def get_average_rating(self, time_period: Optional[str] = None) -> float:
        """Get average rating, optionally filtered by time period"""
        if not self.feedback_data:
            return 0.0
        
        # Filter by time period if specified
        filtered_data = self.feedback_data
        if time_period:
            now = datetime.now()
            filtered_data = []
            
            for entry in self.feedback_data:
                try:
                    timestamp = datetime.fromisoformat(entry.get("timestamp", ""))
                    
                    if time_period == "day" and (now - timestamp).days <= 1:
                        filtered_data.append(entry)
                    elif time_period == "week" and (now - timestamp).days <= 7:
                        filtered_data.append(entry)
                    elif time_period == "month" and (now - timestamp).days <= 30:
                        filtered_data.append(entry)
                except:
                    continue
        
        # Calculate average rating
        ratings = [entry.get("rating", 0) for entry in filtered_data if "rating" in entry]
        if not ratings:
            return 0.0
        
        return sum(ratings) / len(ratings)
    
    def get_common_issues(self, n: int = 5) -> List[str]:
        """Extract common issues from feedback messages"""
        if not self.feedback_data:
            return []
        
        # Extract messages with low ratings
        low_rating_messages = [
            entry.get("message", "")
            for entry in self.feedback_data
            if entry.get("rating", 5) <= 3 and "message" in entry
        ]
        
        # Extract common phrases
        phrases = []
        for message in low_rating_messages:
            # Extract 2-3 word phrases
            words = re.findall(r'\b\w+\b', message.lower())
            for i in range(len(words) - 1):
                phrases.append(f"{words[i]} {words[i+1]}")
            
            for i in range(len(words) - 2):
                phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")
        
        # Count phrase occurrences
        phrase_counter = Counter(phrases)
        
        # Filter out common but uninformative phrases
        stopwords = {"the", "and", "for", "with", "this", "that", "not", "but", "was", "did"}
        informative_phrases = [
            phrase for phrase, count in phrase_counter.items()
            if count >= 2 and not all(word in stopwords for word in phrase.split())
        ]
        
        # Return top N phrases
        return informative_phrases[:n]
    
    def generate_feedback_report(self, output_file: str = "feedback_report.html"):
        """Generate a comprehensive feedback report"""
        if not self.feedback_data:
            logger.warning("No feedback data available for report generation")
            return
        
        # Calculate overall statistics
        total_entries = len(self.feedback_data)
        avg_rating = self.get_average_rating()
        avg_rating_week = self.get_average_rating("week")
        avg_rating_month = self.get_average_rating("month")
        
        # Count ratings
        rating_counts = defaultdict(int)
        for entry in self.feedback_data:
            rating = entry.get("rating")
            if rating is not None:
                rating_counts[rating] += 1
        
        # Extract common issues
        common_issues = self.get_common_issues(10)
        
        # Generate plots
        self._generate_rating_distribution_plot()
        self._generate_rating_trend_plot()
        
        # Create HTML report
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Recipe Chatbot Feedback Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #2c3e50; }}
                .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .stat-box {{ background-color: #f8f9fa; border-radius: 5px; padding: 15px; width: 200px; text-align: center; }}
                .rating {{ font-size: 24px; font-weight: bold; color: #3498db; }}
                .plots {{ display: flex; flex-wrap: wrap; justify-content: space-around; margin: 20px 0; }}
                .plot {{ margin: 10px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <h1>Recipe Chatbot Feedback Report</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>Overall Statistics</h2>
            <div class="stats">
                <div class="stat-box">
                    <h3>Total Feedback</h3>
                    <div class="rating">{total_entries}</div>
                </div>
                <div class="stat-box">
                    <h3>Overall Rating</h3>
                    <div class="rating">{avg_rating:.1f}/5</div>
                </div>
                <div class="stat-box">
                    <h3>Last 7 Days</h3>
                    <div class="rating">{avg_rating_week:.1f}/5</div>
                </div>
                <div class="stat-box">
                    <h3>Last 30 Days</h3>
                    <div class="rating">{avg_rating_month:.1f}/5</div>
                </div>
            </div>
            
            <h2>Rating Distribution</h2>
            <div class="plots">
                <div class="plot">
                    <img src="rating_distribution.png" alt="Rating Distribution">
                </div>
                <div class="plot">
                    <img src="rating_trend.png" alt="Rating Trend">
                </div>
            </div>
            
            <h2>Common Issues</h2>
            <ul>
        """
        
        for issue in common_issues:
            html += f"<li>{issue}</li>\n"
        
        html += """
            </ul>
            
            <h2>Recent Feedback</h2>
            <table>
                <tr>
                    <th>Date</th>
                    <th>Rating</th>
                    <th>Feedback</th>
                </tr>
        """
        
        # Add recent feedback entries
        recent_entries = sorted(
            self.feedback_data, 
            key=lambda x: x.get("timestamp", ""), 
            reverse=True
        )[:20]
        
        for entry in recent_entries:
            timestamp = entry.get("timestamp", "")
            try:
                date = datetime.fromisoformat(timestamp).strftime('%Y-%m-%d')
            except:
                date = timestamp
            
            rating = entry.get("rating", "N/A")
            message = entry.get("message", "")
            
            html += f"""
                <tr>
                    <td>{date}</td>
                    <td>{rating}</td>
                    <td>{message}</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        # Write HTML report
        try:
            with open(output_file, "w") as f:
                f.write(html)
            logger.info(f"Feedback report generated: {output_file}")
        except Exception as e:
            logger.error(f"Error generating feedback report: {e}")
    
    def _generate_rating_distribution_plot(self):
        """Generate rating distribution plot"""
        try:
            plt.figure(figsize=(8, 6))
            
            # Count ratings
            rating_counts = defaultdict(int)
            for entry in self.feedback_data:
                rating = entry.get("rating")
                if rating is not None:
                    rating_counts[rating] += 1
            
            # Create bar chart
            ratings = sorted(rating_counts.keys())
            counts = [rating_counts[r] for r in ratings]
            
            plt.bar(ratings, counts, color='#3498db')
            plt.xlabel('Rating')
            plt.ylabel('Count')
            plt.title('Rating Distribution')
            plt.xticks(ratings)
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            plt.savefig('rating_distribution.png')
            plt.close()
        except Exception as e:
            logger.error(f"Error generating rating distribution plot: {e}")
    
    def _generate_rating_trend_plot(self):
        """Generate rating trend over time plot"""
        try:
            plt.figure(figsize=(10, 6))
            
            # Extract timestamps and ratings
            data = []
            for entry in self.feedback_data:
                timestamp = entry.get("timestamp")
                rating = entry.get("rating")
                
                if timestamp and rating is not None:
                    try:
                        date = datetime.fromisoformat(timestamp)
                        data.append((date, rating))
                    except:
                        continue
            
            # Sort by date
            data.sort(key=lambda x: x[0])
            
            if not data:
                logger.warning("No data available for rating trend plot")
                return
            
            dates = [d[0] for d in data]
            ratings = [d[1] for d in data]
            
            # Calculate 7-day moving average
            window_size = min(7, len(ratings))
            moving_avg = []
            
            for i in range(len(ratings)):
                if i < window_size - 1:
                    # Not enough data for full window
                    window = ratings[:i+1]
                else:
                    # Full window
                    window = ratings[i-window_size+1:i+1]
                
                moving_avg.append(sum(window) / len(window))
            
            # Plot individual ratings and moving average
            plt.scatter(dates, ratings, alpha=0.5, color='#3498db', label='Individual Ratings')
            plt.plot(dates, moving_avg, color='#e74c3c', linewidth=2, label=f'{window_size}-day Moving Average')
            
            plt.xlabel('Date')
            plt.ylabel('Rating')
            plt.title('Rating Trend Over Time')
            plt.ylim(0, 5.5)
            plt.grid(linestyle='--', alpha=0.7)
            plt.legend()
            
            plt.tight_layout()
            plt.savefig('rating_trend.png')
            plt.close()
        except Exception as e:
            logger.error(f"Error generating rating trend plot: {e}")

# Initialize the analyzer
feedback_analyzer = FeedbackAnalyzer() 