# app.py
# Streamlit app for hotel deals classification

import streamlit as st
import pandas as pd
from datetime import datetime
import auxiliary_functions
import config

# Page configuration
st.set_page_config(
    page_title="Hotel Deals Classifier",
    page_icon="🏨",
    layout="wide"
)

# Custom CSS for improved design
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem;
        font-weight: bold;
        border-radius: 8px;
    }
    .result-box {
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stMetric {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: bold;
    }
    .bucket-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        margin: 0.25rem 0;
        width: 100%;
        text-align: center;
    }
    .bucket-low {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    .bucket-medium {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
    }
    .bucket-high {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_baselines_cached():
    """Load baselines with caching."""
    try:
        baselines = auxiliary_functions.load_baselines()
        return baselines
    except Exception as e:
        st.error(f"Error loading baselines: {e}")
        return None


@st.cache_data
def load_price_distribution_cached():
    """Load price distribution with caching."""
    if not config.ENABLE_PRICE_BUCKETS:
        return None
    
    try:
        if config.PRICE_DISTRIBUTION_FILE.exists():
            price_dist = pd.read_csv(config.PRICE_DISTRIBUTION_FILE)
            return price_dist
        else:
            return None
    except Exception as e:
        st.error(f"Error loading price distribution: {e}")
        return None


def get_color_for_classification(classification):
    """Return color based on classification."""
    colors = {
        'Deal': '#27ae60',  # Dark green
        'Good Price': '#3498db',  # Blue
        'Normal Price': '#2c3e50',  # Dark blue
        'Expensive': '#e67e22',  # Orange
        'Insufficient Data': '#7f8c8d'  # Gray
    }
    return colors.get(classification, '#2c3e50')


def main():
    """
    Main Streamlit application for hotel deals classification.
    
    Provides an interactive web interface for evaluating hotel prices using
    statistical z-score analysis with bucket-aware classification.
    
    User Flow:
    1. Select destination (with Las Vegas as default)
    2. Choose check-in date (determines month and week)
    3. Enter search parameters (nights, rooms, adults, kids)
    4. Input total booking price (with validation)
    5. Click "Analyze This Price" button
    6. View comprehensive results:
       - Recommendation banner (BOOK NOW / WAIT / NEUTRAL)
       - Classification, z-score, confidence metrics
       - Hotel price category (Budget/Mid-Range/Premium)
       - Baseline statistics and market context
       - Detailed analysis with booking recommendations
    
    UI Sections:
    - **Sidebar**: System information, bucket distribution, classification criteria
    - **Main Area**: Input form, validation, results display
    - **Footer**: Analysis context and data source
    
    Features:
    - Real-time input validation (price $0-$100k, nights 1-90, etc.)
    - Dual price metrics (standardized + per-night)
    - Color-coded recommendations (green/blue/yellow)
    - Confidence level explanations
    - Bucket-specific analysis (when enabled)
    
    Returns:
        None (Streamlit rendering)
    
    Notes:
        - Uses @st.cache_data for baseline loading performance
        - Supports both bucket-aware and traditional analysis modes
        - Validates inputs before enabling analysis button
    """
    # Header with improved design
    st.markdown('<div class="main-header"><h1>🏨 Hotel Deals Detector</h1><p>Statistical price analysis using historical market data and z-score classification</p></div>', unsafe_allow_html=True)
    
    # Load baselines and price distribution
    with st.spinner("Loading baselines..."):
        baselines = load_baselines_cached()
        price_dist = load_price_distribution_cached()
    
    if baselines is None:
        st.error("❌ Could not load baselines. Run pipeline_build_baselines.py first")
        st.stop()
    
    # Check if buckets are enabled
    buckets_enabled = config.ENABLE_PRICE_BUCKETS and price_dist is not None
    
    if config.ENABLE_PRICE_BUCKETS and price_dist is None:
        st.warning("⚠️ ENABLE_PRICE_BUCKETS is enabled but price_distribution.csv was not found. Run pipeline_build_baselines.py")
        st.info("Using traditional mode without buckets...")
        buckets_enabled = False
    
    # Verify that destination_name exists
    if 'destination_name' not in baselines.columns:
        st.error("❌ Baselines do not contain 'destination_name' column. Regenerate baselines by running pipeline_build_baselines.py")
        st.stop()
    
    # Sidebar with information
    st.sidebar.header("📊 System Information")
    
    # Operation mode
    if buckets_enabled:
        st.sidebar.success("✅ Mode: WITH BUCKETS")
    else:
        st.sidebar.info("ℹ️ Mode: WITHOUT BUCKETS (traditional)")
    
    st.sidebar.metric("Historical Searches Analyzed", f"{len(baselines):,}", help="Total number of market conditions analyzed")
    st.sidebar.metric("Destinations Covered", f"{baselines['destination_final'].nunique():,}", help="Cities and regions in our database")
    st.sidebar.metric("High-Confidence Data Points", f"{(~baselines['low_confidence']).sum():,}", help="Searches with sufficient historical data")
    
    # Confidence explanation
    with st.sidebar.expander("ℹ️ Understanding Confidence Levels"):
        st.markdown("""
        **✅ High Confidence**: Baseline calculated from 10+ observations with bucket-specific data
        
        **⚠️ Medium Confidence**: Limited bucket data, using general market baseline
        
        **🔴 Low Confidence**: Insufficient historical data (< 10 observations) or high price variability
        
        💡 **Tip**: Low confidence doesn't mean the deal is bad – it means less historical data is available for this specific destination/date combination.
        """)
    
    # Show bucket distribution if enabled with improved styling
    if buckets_enabled and 'price_bucket' in baselines.columns:
        st.sidebar.markdown("---")
        st.sidebar.subheader("🏷️ Hotel Category Distribution")
        st.sidebar.caption("Historical data segmented by price tier")
        
        bucket_config = [
            ('low', '💰 Budget', 'bucket-low'),
            ('medium', '🏨 Mid-Range', 'bucket-medium'),
            ('high', '✨ Premium', 'bucket-high')
        ]
        
        total_contexts = len(baselines)
        for bucket_key, bucket_label, css_class in bucket_config:
            count = len(baselines[baselines['price_bucket'] == bucket_key])
            percentage = (count / total_contexts * 100) if total_contexts > 0 else 0
            st.sidebar.markdown(
                f'<div class="bucket-badge {css_class}">{bucket_label}<br/>{count:,} searches ({percentage:.1f}%)</div>',
                unsafe_allow_html=True
            )
    
    # Show thresholds
    st.sidebar.markdown("---")
    st.sidebar.subheader("📏 Classification Criteria")
    st.sidebar.code(f"""
✅ DEAL (Highly Recommended)
   z-score < {config.THRESHOLDS['deal']}
   
👍 GOOD PRICE (Recommended)
   {config.THRESHOLDS['deal']} ≤ z < {config.THRESHOLDS['good_price']}
   
➡️ NORMAL PRICE
   {config.THRESHOLDS['good_price']} ≤ z < {config.THRESHOLDS['normal_upper']}
   
⚠️ EXPENSIVE
   z ≥ {config.THRESHOLDS['normal_upper']}
    """)
    st.sidebar.caption("💡 We recommend booking when z-score < -0.5")
    
    # Main section
    st.header("🔍 Price Evaluation")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Create ID -> name dictionary for selectbox
        # Get unique combinations of destination_final and destination_name
        dest_df = baselines[['destination_final', 'destination_name']].drop_duplicates()
        dest_options = dict(zip(dest_df['destination_final'], dest_df['destination_name']))
        
        # Sort by name for better UX
        sorted_dest_ids = sorted(dest_options.keys(), key=lambda x: dest_options[x])
        
        # Find Las Vegas as default
        default_dest = next((d for d in sorted_dest_ids if 'Las Vegas' in dest_options[d]), sorted_dest_ids[0])
        default_index = sorted_dest_ids.index(default_dest)
        
        # Selectbox shows name, returns ID
        st.markdown("**🌍 Destination** _(Type to search)_")
        destination = st.selectbox(
            "Destination",
            options=sorted_dest_ids,
            format_func=lambda x: dest_options[x],
            index=default_index,
            help="Type the city name to search or select from the list",
            label_visibility="collapsed"
        )
        
        # Show selected name
        selected_name = dest_options[destination]
    
    with col2:
        # Date
        check_in_date = st.date_input(
            "📅 Check-in Date",
            value=datetime.now(),
            help="Hotel check-in date"
        )
        
        month = check_in_date.month
        week_in_month = config.get_week_in_month(check_in_date.day)
    
    # Search parameters in one row
    st.subheader("📝 Search Parameters")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        nights = st.number_input("🌙 Nights", min_value=1, value=2, step=1)
    with col2:
        rooms = st.number_input("🏠 Rooms", min_value=1, value=1, step=1)
    with col3:
        adults = st.number_input("👤 Adults", min_value=1, value=2, step=1)
    with col4:
        kids = st.number_input("👶 Children", min_value=0, value=0, step=1)
    
    # Total price
    st.markdown("---")
    st.markdown("### 💰 Total Booking Price")
    total_price = st.number_input(
        "Enter the complete price for your entire stay",
        min_value=0.0,
        value=450.0,
        step=10.0,
        help="💡 Enter the TOTAL price (not per night). This is the complete amount you'll pay for all nights, rooms, and guests combined.",
        label_visibility="collapsed"
    )
    st.caption("⚠️ **Important**: Enter the TOTAL price for the complete reservation, NOT the price per night")
    
    # Calculate standardized price using correct formula (product)
    denominator = nights * rooms * (adults + kids)
    if denominator > 0:
        price_std = total_price / denominator
    else:
        price_std = 0.0
        st.warning("⚠️ Denominator must be greater than 0")
    
    col_metric1, col_metric2 = st.columns(2)
    with col_metric1:
        st.metric(
            "📊 Price per Night-Room-Person", 
            f"${price_std:.2f}",
            help="This standardized metric allows fair comparison across different bookings"
        )
    with col_metric2:
        price_per_night = total_price / nights if nights > 0 else 0
        st.metric(
            "🌙 Total Price per Night",
            f"${price_per_night:.2f}",
            help="Your total nightly rate (all rooms and guests)"
        )
    
    # Input validation
    validation_errors = []
    if nights < 1 or nights > 90:
        validation_errors.append("⚠️ Nights must be between 1 and 90")
    if rooms < 1 or rooms > 10:
        validation_errors.append("⚠️ Rooms must be between 1 and 10")
    if adults < 1:
        validation_errors.append("⚠️ At least 1 adult required")
    if kids > 20:
        validation_errors.append("⚠️ Maximum 20 children allowed")
    if total_price <= 0:
        validation_errors.append("⚠️ Price must be greater than $0")
    if total_price > 100000:
        validation_errors.append("⚠️ Price seems unrealistic (maximum: $100,000)")
    
    if validation_errors:
        for error in validation_errors:
            st.error(error)
    
    # Evaluation button
    st.markdown("---")
    if st.button("🔍 Analyze This Price", type="primary", use_container_width=True, help="Click to get deal recommendation and detailed analysis", disabled=len(validation_errors) > 0):
        if denominator <= 0:
            st.error("❌ Search parameters are invalid. Check nights, rooms, and people.")
        else:
            with st.spinner("Evaluating price..."):
                # Evaluate using new function with buckets
                result = auxiliary_functions.evaluate_hotel_with_bucket_classification(
                    destination_final=destination,
                    month=month,
                    week_in_month=week_in_month,
                    price_std=price_std,
                    baselines_df=baselines,
                    price_dist_df=price_dist,
                    enable_buckets=buckets_enabled
                )
                
                # Show results with improved design
                st.markdown("---")
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.header("📊 Evaluation Results")
                
                # Show recommendation prominently based on z-score
                if result.get('z_score') is not None:
                    z = result['z_score']
                    # Recommend if Deal OR Good Price (z < -0.5)
                    is_recommended = z < config.THRESHOLDS['good_price']
                    
                    if is_recommended:
                        if z < config.THRESHOLDS['deal']:
                            st.success("## ✅ EXCELLENT DEAL - HIGHLY RECOMMENDED")
                            st.markdown("#### 🎯 This price is significantly below market average")
                        else:
                            st.success("## 👍 GOOD PRICE - RECOMMENDED")
                            st.markdown("#### 💡 This price is below market average - worth booking")
                    else:
                        if z > config.THRESHOLDS['normal_upper']:
                            st.warning("## ⚠️ EXPENSIVE - NOT RECOMMENDED")
                            st.markdown("#### 💭 Consider waiting or checking other options")
                        else:
                            st.info("## ➡️ NORMAL PRICE")
                            st.markdown("#### 📊 This price is within typical market range")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    classification = result['classification']
                    color = get_color_for_classification(classification)
                    st.markdown(f"### 🎯 Classification")
                    st.markdown(
                        f"<div style='background-color: {color}; color: white; padding: 2rem; border-radius: 10px; text-align: center;'><h1 style='color: white; margin: 0;'>{classification}</h1></div>",
                        unsafe_allow_html=True
                    )
                
                with col2:
                    st.markdown(f"### 📈 Z-Score")
                    if result['z_score'] is not None:
                        z_value = result['z_score']
                        z_color = '#2ecc71' if z_value < -0.5 else ('#e67e22' if z_value > 0.5 else '#95a5a6')
                        st.markdown(
                            f"<div style='background-color: {z_color}; color: white; padding: 2rem; border-radius: 10px; text-align: center;'><h1 style='color: white; margin: 0;'>{z_value:.2f}</h1></div>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.metric("", "N/A")
                
                with col3:
                    st.markdown(f"### ✅ Confidence")
                    confidence = result['confidence']
                    confidence_emoji = "✅" if confidence == 'high' else "⚠️"
                    confidence_color = '#2ecc71' if confidence == 'high' else '#e67e22'
                    st.markdown(
                        f"<div style='background-color: {confidence_color}; color: white; padding: 2rem; border-radius: 10px; text-align: center;'><h2 style='color: white; margin: 0;'>{confidence_emoji} {confidence.upper()}</h2></div>",
                        unsafe_allow_html=True
                    )
                
                # Show bucket information if available
                if buckets_enabled and result.get('price_bucket'):
                    st.markdown("---")
                    st.subheader("🏷️ Price Category Analysis")
                    
                    bucket = result['price_bucket']
                    bucket_label = config.BUCKET_LABELS.get(bucket, bucket.capitalize())
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Price Category", bucket_label,
                                 help="Based on your search price position in the market")
                    
                    if result.get('market_percentiles'):
                        percentiles = result['market_percentiles']
                        with col2:
                            st.metric("Market Median", f"${percentiles['p50']:.2f}")
                        with col3:
                            if result.get('relative_price_index'):
                                rpi = result['relative_price_index']
                                st.metric("Relative Index", f"{rpi:.2f}x",
                                         help="Your price / market median")
                    
                    # Show percentile ranges
                    if result.get('market_percentiles'):
                        st.info(f"""
                        **Price ranges for {selected_name}:**
                        - 💰 Budget (low): up to ${percentiles['p25']:.2f}
                        - 🏨 Mid-Range (medium): ${percentiles['p25']:.2f} - ${percentiles['p75']:.2f}
                        - ✨ Premium (high): from ${percentiles['p75']:.2f}
                        
                        💡 *Categories are based on price position, not hotel quality*
                        """)
                    
                    # Detect and show boundary case warning
                    if result.get('market_percentiles') and result.get('price_bucket'):
                        p25 = result['market_percentiles']['p25']
                        p75 = result['market_percentiles']['p75']
                        boundary_margin = 0.15
                        
                        near_p25 = abs(price_std - p25) / p25 < boundary_margin
                        near_p75 = abs(price_std - p75) / p75 < boundary_margin
                        
                        if near_p25 or near_p75:
                            threshold = p25 if near_p25 else p75
                            st.info(f"""
                            ℹ️ **Boundary Case Detected:** Your price (${price_std:.2f}) is close to a category 
                            threshold (${threshold:.2f}). Small price changes could shift the category and 
                            significantly affect the deal classification.
                            """)
                    
                    if result.get('used_fallback'):
                        st.warning("⚠️ **Note:** Limited data for this category. General market baseline was used for better accuracy.")
                
                # Additional information
                if result['baseline_info']:
                    st.markdown("---")
                    st.subheader("📊 Baseline Information")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    baseline = result['baseline_info']
                    bucket_context = ""
                    if buckets_enabled and result.get('price_bucket'):
                        bucket_label = config.BUCKET_LABELS.get(result['price_bucket'], '')
                        bucket_context = f"{bucket_label} Category "
                    
                    with col1:
                        st.metric(
                            f"💵 {bucket_context}Mean",
                            f"${baseline['mean']:.2f}",
                            help=f"Average price for {bucket_context.lower()}hotels in this period"
                        )
                    
                    with col2:
                        st.metric(
                            "📏 Standard Deviation",
                            f"${baseline['std']:.2f}"
                        )
                    
                    with col3:
                        st.metric(
                            "📋 Observations",
                            f"{baseline['count']:,.0f}"
                        )
                    
                    if baseline.get('bucket') and baseline['bucket'] != 'mixed':
                        bucket_label = config.BUCKET_LABELS.get(baseline['bucket'], baseline['bucket'])
                        st.caption(f"📊 Category-specific baseline for {bucket_label} hotels")
                    
                    # Interpretation
                    st.markdown("---")
                    st.subheader("💡 Detailed Analysis")
                    
                    if classification == 'Deal':
                        msg = "**🎉 Excellent Opportunity!** This price is significantly below market average."
                        if buckets_enabled and result.get('price_bucket'):
                            bucket_label = config.BUCKET_LABELS.get(result['price_bucket'], result['price_bucket'])
                            msg += f" Compared to other **{bucket_label}** hotels in {selected_name}, this is a highly recommended deal."
                            if baseline:
                                msg += f"\n\n📊 *Z-score compares against {bucket_label.lower()} category baseline (${baseline['mean']:.2f}), not the overall market median.*"
                        msg += "\n\n### ✅ Recommendation: BOOK NOW\nPrices like this are rare and unlikely to last long."
                        st.success(msg)
                    elif classification == 'Good Price':
                        msg = "**👍 Good Price.** This price is below market average."
                        if buckets_enabled and result.get('price_bucket'):
                            bucket_label = config.BUCKET_LABELS.get(result['price_bucket'], result['price_bucket'])
                            msg += f" For a **{bucket_label}** hotel, this is a good booking option."
                            if result.get('relative_price_index') and result.get('market_percentiles'):
                                rpi = result['relative_price_index']
                                msg += f"\n\n💡 *Your Relative Index ({rpi:.2f}x) compares to the overall market median, while the z-score ({z_value:.2f}) compares within the {bucket_label.lower()} category.*"
                        msg += "\n\n### ✅ Recommendation: WORTH BOOKING\nThis is a fair deal - consider booking if dates match your needs."
                        st.success(msg)
                    elif classification == 'Normal Price':
                        msg = "**➡️ Normal Price.** This price is within the expected range for this destination and season."
                        msg += "\n\n### 💭 Recommendation: NEUTRAL\nStandard market price. Book if location and dates fit your travel plans."
                        st.info(msg)
                    elif classification == 'Expensive':
                        msg = "**⚠️ High Price.** This price is above market average."
                        if buckets_enabled and result.get('price_bucket'):
                            bucket_label = config.BUCKET_LABELS.get(result['price_bucket'], result['price_bucket'])
                            msg += f" Even for **{bucket_label}** hotels, you could likely find better options."
                        msg += "\n\n### ⚠️ Recommendation: WAIT OR SHOP AROUND\nBetter deals are likely available. Consider checking other hotels or dates."
                        st.warning(msg)
                    else:
                        st.info("""
                        **ℹ️ Insufficient Data.** No historical baseline exists for this specific context 
                        (destination + month + week of month). Cannot provide classification.
                        """)
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer with context
    st.markdown("---")
    st.caption(f"📍 **Analysis Context:** {selected_name} • Month {month} • Week {week_in_month} of the month")
    st.caption(f"💾 **Data Source:** {config.BASELINES_FILE}")


if __name__ == "__main__":
    main()
