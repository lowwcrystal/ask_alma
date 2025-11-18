# Professor Comparison Multi-Query Retrieval Fix

## Problem

When users asked to compare two professors, the RAG system would only retrieve context for one professor:

**Before Fix:**
```
Q: "How does Professor Brian Borowski compare to Professor Jae Lee?"
Retrieved: 7 chunks about Borowski, 0 about Jae Lee ❌
Result: "I don't have information about Professor Jae Lee..."
```

**Root Cause:** Single-query vector similarity search would favor one professor over the other, causing all top-K results to be about the same professor.

## Solution

Implemented **multi-query retrieval** that:
1. Detects comparison queries using regex patterns
2. Extracts both professor names
3. Retrieves results for each professor separately  
4. Combines and deduplicates results for balanced context

**After Fix:**
```
Q: "How does Professor Brian Borowski compare to Professor Jae Lee?"
Retrieved: 5 chunks about Borowski, 5 about Jae Lee ✅
Result: Comprehensive comparison with ratings and feedback for both
```

## Implementation

### 1. Comparison Detection (`detect_professor_comparison`)

Detects comparison queries using regex patterns:
- "Compare Professor X and Professor Y"
- "How does Professor X compare to Professor Y"
- "Which is better: Professor X or Professor Y"
- "Professor X versus Professor Y"

Returns `(professor1, professor2)` tuple if comparison detected, `None` otherwise.

### 2. Professor-Specific Retrieval (`retrieve_for_professor`)

Creates a targeted query for a specific professor:
```python
prof_query = f"Professor {professor_name} teaching style reviews rating"
```

Then retrieves chunks where:
- Content or source mentions the professor name
- Sorted by similarity to the targeted query
- Limited to K/2 results (5 chunks by default)

### 3. Multi-Query Integration in `rag_answer`

```python
comparison = detect_professor_comparison(question)

if comparison:
    prof1, prof2 = comparison
    # Retrieve 5 chunks for each professor
    prof1_rows = retrieve_for_professor(prof1, ...)
    prof2_rows = retrieve_for_professor(prof2, ...)
    # Combine, deduplicate, and sort by similarity
    rows = combine_and_deduplicate(prof1_rows, prof2_rows)
else:
    # Normal single-query retrieval
    rows = standard_retrieval(question, ...)
```

## Supported Comparison Patterns

All of these now work correctly:

✅ "Compare Professor Brian Borowski and Professor Jae Lee"  
✅ "How does Professor Sala-i-Martin compare to Professor Schmitt-Grohe?"  
✅ "Which is better: Professor X or Professor Y?"  
✅ "Professor X versus Professor Y for Data Structures"  
✅ "Brian Borowski vs Jae Lee" (without "Professor")  

## Test Results

### Test 1: Brian Borowski vs Jae Lee
```
Detected: ✅ "brian borowski vs jae lee"
Retrieved: 5 chunks for Borowski, 5 for Jae Lee
Answer: Comprehensive comparison including:
  - Overall ratings (3.04 vs 3.28)
  - Teaching styles
  - Workload details
  - Pros and cons for each
  - Decision guidance
```

### Test 2: Xavier Sala-i-Martin vs Stephanie Schmitt-Grohe
```
Detected: ✅ "xavier sala-i-martin vs stephanie schmitt-grohe"
Retrieved: 5 chunks for Sala-i-Martin, 5 for Schmitt-Grohe  
Answer: Fair comparison with equal coverage
```

### Test 3: Sunil Gulati vs Waseem Noor
```
Detected: ✅ "sunil gulati vs waseem noor"
Retrieved: 5 chunks for Gulati, 0 for Noor (not in database)
Answer: Provided Gulati's review and noted lack of data for Noor
```

## Files Modified

**`src/embedder/rag_query.py`**

### Added Functions:
1. **`detect_professor_comparison()`** (lines 415-450)
   - Regex patterns to detect comparisons
   - Extracts professor names
   - Validates name format

2. **`retrieve_for_professor()`** (lines 453-494)
   - Targeted retrieval for specific professor
   - Filters by professor name in content/source
   - Returns top-K/2 results

### Modified Functions:
3. **`rag_answer()`** (lines 570-596)
   - Checks for comparison queries
   - Routes to multi-query retrieval if comparison detected
   - Falls back to normal retrieval otherwise

## Configuration

Adjust these values in `rag_query.py` if needed:

```python
TOP_K = 10  # Total chunks to retrieve
per_prof_limit = TOP_K // 2  # Chunks per professor (default: 5 each)
```

## Edge Cases Handled

✅ **One professor not in database**: Returns available professor's data  
✅ **Duplicate chunks**: Deduplication by ID ensures no repeats  
✅ **Similar professor names**: Regex patterns validate name format  
✅ **Non-comparison queries**: Falls back to normal retrieval  
✅ **School filtering**: Respects user's school profile while allowing CULPA

## Benefits

1. **Fair Comparisons**: Equal representation of both professors
2. **Better User Experience**: Students get complete information for decisions
3. **Accurate Ratings**: Both professors' ratings included in response
4. **Balanced Context**: LLM has access to both perspectives

## Future Enhancements

Potential improvements:
- Support for comparing 3+ professors
- Adjust chunk ratio based on query focus (e.g., 7:3 instead of 5:5)
- Cache comparison results for frequently asked pairs
- Add course-specific filtering when mentioned in query

## Usage

No changes needed in frontend or API. The improvement is transparent to users:

```python
# User asks comparison question
question = "Compare Professor X and Professor Y for COURSE"

# Backend automatically detects and handles it
result = rag_answer(question, user_id=user_id)

# Result includes balanced data for both professors
```

## Debug Output

When testing, you'll see debug output:
```
[DEBUG] Detected comparison: xavier sala-i-martin vs stephanie schmitt-grohe
[DEBUG] Retrieved 5 chunks for xavier sala-i-martin, 5 chunks for stephanie schmitt-grohe
```

This can be removed or made conditional for production.

## Testing

Run the test script:
```bash
python3 test_professor_comparison.py
```

Expected output:
- ✅ Comparison detected
- ✅ Chunks retrieved for both professors
- ✅ Balanced, comprehensive answer with ratings

