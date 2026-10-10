#!/usr/bin/env python3
"""
Quick Revenue Estimator untuk Dragon Arrow Escape
Hitung estimasi pendapatan berdasarkan active users
"""

def format_rupiah(amount_usd):
    """Convert USD to IDR (rate: 1 USD = 15,700 IDR)"""
    idr = amount_usd * 15700
    return f"Rp {idr:,.0f}".replace(",", ".")

def estimate_revenue(daily_users, session_minutes=10):
    """
    Estimasi revenue berdasarkan active users
    
    Args:
        daily_users: Jumlah active users per hari
        session_minutes: Rata-rata durasi main per session (default 10 menit)
    """
    
    print("="*70)
    print(f"💰 ESTIMASI PENDAPATAN - Dragon Arrow Escape")
    print("="*70)
    print(f"\n📊 Assumptions:")
    print(f"   • Daily Active Users: {daily_users:,}")
    print(f"   • Session Duration: {session_minutes} minutes")
    print(f"   • Geography Mix: 30% tier-1, 70% tier-2/3")
    
    # Ad frequency per session
    rewarded_per_session = 2 if session_minutes >= 10 else 1
    interstitial_per_session = 1 if session_minutes >= 5 else 0
    banner_impressions = session_minutes * 5  # 5 impressions per minute di menu
    
    print(f"\n📺 Ad Frequency per Session:")
    print(f"   • Rewarded Ads: {rewarded_per_session}x (user triggered)")
    print(f"   • Interstitial Ads: {interstitial_per_session}x (auto, cooldown 3min)")
    print(f"   • Banner Impressions: {banner_impressions}x (menu screens)")
    
    # Daily impressions
    rewarded_impressions = daily_users * rewarded_per_session
    interstitial_impressions = daily_users * interstitial_per_session
    banner_impressions_total = daily_users * banner_impressions
    
    # CPM (blended rate: tier-1 countries pay more)
    rewarded_cpm = 15.0  # $10-30, using middle
    interstitial_cpm = 5.0  # $3-8, using middle
    banner_cpm = 1.0  # $0.5-2, using middle
    
    # Daily revenue
    rewarded_revenue = (rewarded_impressions / 1000) * rewarded_cpm
    interstitial_revenue = (interstitial_impressions / 1000) * interstitial_cpm
    banner_revenue = (banner_impressions_total / 1000) * banner_cpm
    
    daily_total = rewarded_revenue + interstitial_revenue + banner_revenue
    monthly_total = daily_total * 30
    yearly_total = daily_total * 365
    
    print(f"\n💵 DAILY REVENUE BREAKDOWN:")
    print(f"   Rewarded:     {rewarded_impressions:>8,} impressions × ${rewarded_cpm} CPM = ${rewarded_revenue:>7,.2f}")
    print(f"   Interstitial: {interstitial_impressions:>8,} impressions × ${interstitial_cpm} CPM = ${interstitial_revenue:>7,.2f}")
    print(f"   Banner:       {banner_impressions_total:>8,} impressions × ${banner_cpm} CPM = ${banner_revenue:>7,.2f}")
    print(f"   " + "-"*66)
    print(f"   TOTAL:        ${daily_total:>7,.2f}/day")
    
    print(f"\n💰 PROJECTED EARNINGS:")
    print(f"   Daily:   ${daily_total:>8,.2f}  ({format_rupiah(daily_total)})")
    print(f"   Weekly:  ${daily_total*7:>8,.2f}  ({format_rupiah(daily_total*7)})")
    print(f"   Monthly: ${monthly_total:>8,.2f}  ({format_rupiah(monthly_total)})")
    print(f"   Yearly:  ${yearly_total:>8,.2f}  ({format_rupiah(yearly_total)})")
    
    # Fill rate impact
    fill_rate = 0.85  # 85% typical
    actual_monthly = monthly_total * fill_rate
    
    print(f"\n⚠️  REALISTIC ESTIMATE (85% fill rate):")
    print(f"   Monthly: ${actual_monthly:,.2f}  ({format_rupiah(actual_monthly)})")
    
    # Scaling scenarios
    print(f"\n📈 SCALING SCENARIOS:")
    scenarios = [
        (1000, "Soft Launch"),
        (5000, "Good Traction"),
        (10000, "Successful Game"),
        (50000, "Viral Hit"),
        (100000, "Top Chart")
    ]
    
    for users, label in scenarios:
        scenario_monthly = (daily_total * (users / daily_users) * 30 * fill_rate)
        print(f"   {users:>7,} users/day: ${scenario_monthly:>9,.2f}/month  ({format_rupiah(scenario_monthly)})  [{label}]")
    
    # Optimization tips
    print(f"\n💡 TIPS TO INCREASE REVENUE:")
    print(f"   1. Encourage rewarded ads (highest CPM)")
    print(f"   2. Target tier-1 countries (US, UK, AU)")
    print(f"   3. Enable mediation (more ad sources)")
    print(f"   4. Optimize ad placement (better engagement)")
    print(f"   5. A/B test ad frequency")
    
    print(f"\n🎯 MONETIZATION HEALTH METRICS:")
    arpdau = daily_total / daily_users  # Average Revenue Per Daily Active User
    print(f"   ARPDAU: ${arpdau:.4f} per user")
    
    if arpdau < 0.05:
        print(f"   Status: 🔴 Low - Increase ad frequency or targeting")
    elif arpdau < 0.15:
        print(f"   Status: 🟡 Good - Room for optimization")
    else:
        print(f"   Status: 🟢 Excellent - Well monetized!")
    
    print("="*70)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        try:
            users = int(sys.argv[1])
            session_min = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            estimate_revenue(users, session_min)
        except ValueError:
            print("Usage: python estimate_revenue.py <daily_users> [session_minutes]")
            print("Example: python estimate_revenue.py 5000 12")
            sys.exit(1)
    else:
        # Default scenarios
        print("\n" + "="*70)
        print("CONSERVATIVE SCENARIO (1K users)")
        print("="*70)
        estimate_revenue(1000, 10)
        
        print("\n\n" + "="*70)
        print("TARGET SCENARIO (5K users)")
        print("="*70)
        estimate_revenue(5000, 12)
        
        print("\n\n" + "="*70)
        print("SUCCESS SCENARIO (10K users)")
        print("="*70)
        estimate_revenue(10000, 15)
