# 🔍 Quick Reference: Running the Data Analysis

**Last Updated:** April 15, 2026

---

## TL;DR - Run This Now

```bash
cd f:\FYP\Travello\backend
python manage.py analyze_itinerary_ranker_data --verbose
```

## ⏱️ What This Command Does (Without Training/Saving)

```
READS ← Database (Places, Itineraries, Users)
  ↓
ANALYZES ← Feature distributions, data quality
  ↓
REPORTS ← Statistics, recommendations
  ↓
OUTPUTS → Terminal + JSON log file
```

**Time:** ~2-5 seconds for typical data size  
**Side effects:** None (read-only)  
**Output files:** `logs/ranker_data_analysis_YYYYMMDD_HHMMSS.json`

---

## 📊 Understanding the Output

### Section 1: DATA OVERVIEW
```
Total Itineraries: 5
Total Users: 3
Total Places: 130
Total Training Samples: 650
Positive Samples: 85
Negative Samples: 565
Class Balance: "85/565"
Class Ratio: "13.08%"
```

**What it means:**
- 5 itineraries = 5 user trips saved
- 650 samples = 130 places × 5 itineraries
- 13.08% positive = 13% of samples are places that were actually selected
- **Good range:** 10-30% positive ratio

**⚠️ If:**
- Total samples < 100 → Insufficient data
- Positive samples < 10 → Too few real examples
- Class ratio > 95% negative → Highly imbalanced

---

### Section 2: PLACES DATABASE
```
Categories by Category:
  • Religious: 20
  • History: 32
  • Food: 42
  • Nature: 18
  • Shopping: 15
  • Modern: 8
  • Culture: 10
  • Other: 5

Budget Levels:
  • LOW: 85
  • MEDIUM: 38
  • LUXURY: 14

Average Rating: 4.31
Places with Rating: 128
```

**What it means:**
- Good diversity of categories
- Coverage of all budget levels
- Most places have ratings (no major gaps)

---

### Section 3: FEATURE ANALYSIS

#### Distribution Example:
```
Moods (User Preferences):
  • RELAXING: 120
  • SPIRITUAL: 95
  • HISTORICAL: 150
  • FOODIE: 89
  • FUN: 96
  • SHOPPING: 45
  • NATURE: 85
  • ROMANTIC: 32
  • FAMILY: 23

Budgets (User Budget Levels):
  • LOW: 250
  • MEDIUM: 300
  • LUXURY: 100

Categories (Place Categories):
  • Religious: 85
  • History: 124
  • Food: 165
  • Nature: 89
  • Shopping: 59
  • ...

Rating Distribution:
  min: 3.9
  max: 4.8
  mean: 4.31
  median: 4.35

Visit Minutes:
  min: 30
  max: 300
  mean: 105
```

**Translation:**
- All 9 moods represented ✅ (good for model diversity)
- Most users choose MEDIUM budget
- Food places most common
- Ratings tightly clustered (3.9-4.8)

**⚠️ Red flags:**
- Only 1-2 moods with samples → Model won't learn varied preferences
- All places rated 4.5+ → Unrealistic selection bias
- Only 1 budget category → Over-fitted model

---

### Section 4: DATA QUALITY
```
Total Samples: 650
Valid Samples: 645
Missing Rating: 2
Missing Interests: 8
Missing Mood: 0

Data Completeness:
  rating: 99.7%
  interests: 98.8%
  mood: 100.0%

Readiness: READY
```

**What it means:**
- 99.7% of samples have ratings ✅
- Almost no missing data
- Status: READY for training

**⚠️ If Readiness = INSUFFICIENT:**
- Add more itineraries OR
- Generate synthetic data

---

### Section 5: PLACE POPULARITY

#### Most Selected:
```
• Badshahi Mosque — 5x selected (rating: 4.8⭐)
• Shalimar Gardens — 5x selected (rating: 4.6⭐)
• Lahore Fort — 4x selected (rating: 4.7⭐)
• Data Darbar — 4x selected (rating: 4.5⭐)
• Walled City — 3x selected (rating: 4.6⭐)
```

**Interpretation:**
- Popular places: prestigious, high-rated, "must-see"
- Model should learn to prioritize these for cultural itineraries
- ✅ Indicates real user preferences

#### Least Selected:
```
• Brandreth Road Market — 0x selected (rating: 3.9⭐)
• Arfa Software Tech Park — 0x selected (rating: 4.0⭐)
• Modern Venues — mostly not selected
```

**Interpretation:**
- Less appealing despite low ratings
- Niche attractions (tech park not tourist-focused)
- Model will learn these lower in rankings

#### Never Selected:
```
Never Selected: 45 places
```

**Interpretation:**
- 45 places not yet in any itinerary
- Model lacks training signal for these
- When model encounters: will use features to estimate

**⚠️ If > 50% never selected:**
- Highly incomplete training data
- Consider adding synthetic preferences

---

### Section 6: RECOMMENDATIONS

#### Example 1 (Sufficient Data):
```
✅ READY FOR TRAINING: 650 samples (85 positive, 565 negative) 
   with 13.08% positive ratio.
```
**Action:** Proceed to Phase 2 - Feature engineering

#### Example 2 (Insufficient Samples):
```
⚠️ INSUFFICIENT DATA: Need at least 100 training samples. 
   Current: 42. Generate more itineraries.
```
**Action:** Have users create more itineraries, come back after

#### Example 3 (Too Few Positive):
```
⚠️ IMBALANCED: Too few positive examples (5). 
   Need at least 50 selected places across itineraries.
```
**Action:** need 10+ itineraries, not just 2

#### Example 4 (Extreme Imbalance):
```
⚠️ SKEWED: Class ratio too imbalanced (3.2% positive). 
   Model will struggle with minority class.
```
**Action:** Use weighted loss function during training

---

## 🔧 Command Options

### Verbose Mode (Detailed Output)
```bash
python manage.py analyze_itinerary_ranker_data --verbose
```
**Output:** More detailed step-by-step progress

### Limit to Sample Itineraries
```bash
python manage.py analyze_itinerary_ranker_data --sample 10
```
**Use case:** Fast preview on large dataset

### Analyze Different City
```bash
python manage.py analyze_itinerary_ranker_data --city Islamabad
```
**Use case:** Test on other cities when available

### Combine Options
```bash
python manage.py analyze_itinerary_ranker_data --verbose --sample 50 --city Lahore
```

---

## 📈 What the JSON Report Contains

Saved to: `logs/ranker_data_analysis_20260415_143022.json`

```json
{
  "timestamp": "2026-04-15T14:30:22.123456",
  "city": "Lahore",
  "data_overview": {
    "total_itineraries": 5,
    "total_users": 3,
    "total_places": 130,
    "total_training_samples": 650,
    "positive_samples": 85,
    ...
  },
  "places_stats": {...},
  "feature_analysis": {...},
  "data_quality": {...},
  "place_popularity": {...},
  "data_issues": [...],
  "recommendation": "✅ READY FOR TRAINING..."
}
```

**Use case:** Share report with team, track over time

---

## 🎓 Typical Output Examples

### Scenario 1: Good Data (Go Proceed)
```
✅ READY FOR TRAINING: 890 samples (156 positive, 734 negative) with 17.5% positive ratio
```
→ Next: `train_ai_ranker.py` (Phase 2)

### Scenario 2: Not Enough Data Yet
```
⚠️ INSUFFICIENT DATA: Need at least 100 training samples. Current: 38.
```
→ Action: Have 5+ users create itineraries, try again next week

### Scenario 3: Balanced Dataset (Excellent)
```
✅ READY FOR TRAINING: 1200 samples (400 positive, 800 negative) with 33% positive ratio
```
→ Next: Prepare features for LightGBM training

### Scenario 4: Heavy Class Imbalance
```
⚠️ SKEWED: Class ratio too imbalanced (2.5% positive). 
Model will struggle with minority class.

Recommendation: Use class_weight='balanced' in LightGBM training
```

---

## 🔄 Typical Workflow

```
Week 1: Setup
├─ Create management command (✅ DONE)
└─ Run analyze_itinerary_ranker_data.py

Week 2: Collect Real Data
├─ Have users create itineraries (10+ different users)
├─ Get 5+ trips with full day plans
└─ Review data with analyze_itinerary_ranker_data.py

Week 3: Prepare Features
├─ If data sufficient (>100 samples):
│  └─ Normalize features
│  └─ Handle missing values
│  └─ Create train/test split
└─ If data insufficient:
   └─ Generate synthetic data OR
   └─ Get more real itineraries

Week 4: Train Model
├─ Run: python manage.py train_ai_ranker.py
├─ Validate on test set
└─ Evaluate against rule-based baseline

Week 5: Deploy
├─ Load model in ai_ranker_service.py
├─ Test end-to-end
└─ Monitor performance
```

---

## 🚨 Common Issues & Solutions

### Issue 1: Command Not Found
```bash
$ python manage.py analyze_itinerary_ranker_data
CommandError: Command 'analyze_itinerary_ranker_data' not found
```

**Solution:**
```bash
# Create directories
mkdir -p backend/itineraries/management/commands

# Create __init__.py files
touch backend/itineraries/management/__init__.py
touch backend/itineraries/management/commands/__init__.py
```

### Issue 2: No Itineraries in Database
```
Total Itineraries: 0
Recommendation: ⚠️ INSUFFICIENT DATA: Create at least 1 itinerary
```

**Solution:**
- Visit frontend
- Create test itinerary (Day trip to Lahore)
- View backend to confirm saved
- Re-run analysis

### Issue 3: Missing Place Ratings
```
Places with Rating: 98/130
Missing Rating: 32 places
```

**Solution:**
- Add ratings in fixture data OR
- Model will use default (3.5) for missing

### Issue 4: Memory Error
```
MemoryError: Unable to allocate X GB
```

**Solution:**
```bash
# Limit to sample
python manage.py analyze_itinerary_ranker_data --sample 50
```

---

## 📝 Next Actions

### Do Now (5 minutes)
```bash
python manage.py analyze_itinerary_ranker_data --verbose
# Review output for recommendation
```

### Today (30 minutes)
```bash
# 1. Read the report
# 2. Check data status
# 3. Identify gaps

# If status = READY:
#   → Document findings
# If status != READY:
#   → Create test itineraries
#   → Re-run analysis
```

### This Week
```bash
# Share analysis report with team
# Discuss readiness for Phase 2 (feature engineering)
# Plan next data collection/generation steps
```

---

## 💡 Pro Tips

**Tip 1: Check both terminal AND JSON**
```bash
# Terminal shows formatted summary
python manage.py analyze_itinerary_ranker_data

# JSON file contains full details (importable for further analysis)
cat logs/ranker_data_analysis_*.json | python -m json.tool
```

**Tip 2: Track over time**
```bash
# Each run creates new timestamped file
# Compare multiple runs to see progression
# Graph: Samples over time → indicates adoption
```

**Tip 3: Focus on positive samples**
```
Key metric: Count of POSITIVE SAMPLES
- < 10: Too few (not enough real preferences)
- 10-50: Minimal (may struggle)
- 50-200: Good! (enough diversity)
- > 200: Excellent (rich signal)
```

**Tip 4: Validate before training**
```bash
# Always run this BEFORE attempting to train
python manage.py analyze_itinerary_ranker_data --verbose

# Only proceed to train_ai_ranker.py if recommendation = READY
```

---

## 🎯 Success Checklist

Before training the ML model, confirm:

- [ ] Command runs without errors
- [ ] Total samples: > 100
- [ ] Positive samples: > 20
- [ ] Data completeness: > 95%
- [ ] Readiness status: READY
- [ ] All 9 moods represented (optional but good)
- [ ] Multiple users in data (> 3)
- [ ] Recommendation states "READY FOR TRAINING"

---

**Ready? Run it now:** 
```bash
python manage.py analyze_itinerary_ranker_data --verbose
```

Then come back with the output! 🚀
