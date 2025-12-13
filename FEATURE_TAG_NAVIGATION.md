# Feature Idea: Tag/Marker Navigation System

**Date:** December 13, 2025  
**Status:** Design Phase - Not Implemented

## Problem Statement
When analyzing large DLT logs, certain log messages are critical markers (e.g., "resumed from STR" indicating system state changes). Currently, users must scroll through search results to find these important points. We need a way to:
- Define specific patterns as navigable tags/markers
- Quickly jump between occurrences of these tagged messages
- Support multiple tag types for different categories of important logs

## Use Case Example
User needs to track system resume events ("resumed from STR"). These mark new cycles in the log and are crucial reference points. User wants to:
1. Configure "resumed from STR" as a tag named "System Resume"
2. Navigate: Click button to jump from first → second → third occurrence
3. Use multiple tags simultaneously (System Resume, Critical Errors, Power Events, etc.)

## Design Options Considered

### Option 1: Bookmark-Style Tags (Recommended)
- Separate "Tags/Bookmarks" manager dialog (independent from search)
- Each tag definition:
  - **Name**: User-friendly label (e.g., "System Resume")
  - **Pattern**: Text or regex to match (e.g., "resumed from STR")
  - **Icon/Symbol**: Visual indicator (🔄, ⚠️, 🔌, etc.)
  - **Color**: Optional background highlight
- Visual: Add narrow gutter column (leftmost) showing tag icons
- Navigation: Toolbar buttons [◀ Prev Tag] [▶ Next Tag] + dropdown for tag type selection
- Limit: Support 5-10 different tag types

### Option 2: Enhanced Search with Navigation Mode
- Extend existing search dialog with "Enable Navigation" checkbox
- Patterns marked for navigation get special treatment
- Simpler UI but makes search dialog more complex

### Option 3: Quick Tag System
- Right-click any row → "Tag This Pattern"
- Auto-creates marker based on row content
- Fast but less precise

## Recommended Implementation Approach

### 1. Tag Manager Dialog
**Menu: Tags → Manage Tags**

Features:
- Add/Edit/Remove tag definitions
- Tag properties: name, pattern (text/regex), icon, color
- Save/Load tag configurations to JSON files (shareable like pattern files)
- Limit: 10 tag types maximum
- Enable/Disable individual tags

### 2. Visual Indicators
- Add icon column to main table (leftmost, like line numbers)
- Each tag type shows distinct icon/symbol
- Tooltip on hover shows tag name
- Optional: Subtle background color overlay

### 3. Navigation Controls

**Toolbar additions:**
- [⬆️ Prev Tag] button
- [⬇️ Next Tag] button
- Dropdown: Select tag type (or "All Tags")
- Current tag: Display which tag is active

**Keyboard shortcuts:**
- Ctrl+Up / Ctrl+Down: Navigate tags
- Or F2 / Shift+F2

**Status bar:**
- Show: "Tag 3 of 15: System Resume"

**Behavior:**
- Cycle navigation: Next from last wraps to first, Prev from first wraps to last
- Scroll to and highlight current tagged row
- Works independently of search highlighting

### 4. Integration Points
- Tags work independently from search patterns
- Can combine: perform search + use tag navigation within results
- Tags persist across application sessions
- Re-apply tags automatically when loading new files
- Update tag matches when new files loaded

## Technical Implementation Details

### Data Structures
```python
# Tag definition
class TagDefinition:
    name: str
    pattern: str
    is_regex: bool
    icon: str
    color: str (hex)
    enabled: bool

# Tag matches storage
tag_matches: Dict[str, List[int]]  # tag_name → list of message indices

# Current navigation state
current_tag_type: str  # Which tag is active for navigation
current_position: int  # Current index within that tag's matches
```

### Core Methods Needed
- `apply_tags()`: Scan all messages and build tag_matches dict
- `navigate_next_tag(tag_name)`: Jump to next occurrence
- `navigate_prev_tag(tag_name)`: Jump to previous occurrence
- `update_tag_column()`: Refresh visual indicators in table
- `save_tag_config()`: Export tags to JSON
- `load_tag_config()`: Import tags from JSON

### UI Components
- **TagManagerDialog**: Configure tag definitions
- **Tag column**: QTableWidget leftmost column or custom delegate
- **Navigation toolbar**: Buttons + dropdown
- **Tag config files**: JSON format for sharing

### Performance Considerations
- Pre-index tagged message positions when applying tags
- Only scan when tags change or new files loaded
- Use efficient search (compiled regex if needed)
- Cache tag match positions

## UI Flow Example
```
1. User: Menu → Tags → Manage Tags
2. User: Add new tag
   - Name: "System Resume"
   - Pattern: "resumed from STR"
   - Icon: 🔄
   - Color: #FFCC99
3. User: Click "Apply"
   → App scans all messages
   → Finds 15 matches
   → Shows 🔄 icon in gutter for those rows
4. User: Click [Next Tag ⬇️] button
   → Jumps to row with first "System Resume"
   → Status shows: "Tag 1 of 15: System Resume"
5. User: Click [Next Tag ⬇️] again
   → Jumps to second occurrence
   → Status shows: "Tag 2 of 15: System Resume"
6. User: Select different tag from dropdown
   → Now navigates different tag type
```

## Design Questions to Resolve

1. **Scope**: Should tags be global (apply to all files) or per-session?
   - **Suggestion**: Global config saved to file, applied to whatever files are loaded

2. **Priority**: If one message matches multiple tags, which icon to show?
   - **Suggestion**: Show multiple icons side-by-side, or show highest priority tag (user-definable order)

3. **Tag List Panel**: Should there be a separate panel showing all tagged messages (like search results window)?
   - **Suggestion**: Yes, optional "Show Tag List" window with all occurrences

4. **Manual Tagging**: Allow right-click to tag individual rows without pattern?
   - **Suggestion**: Phase 2 feature - focus on pattern-based tagging first

5. **Tag File Format**: Compatible with pattern files or separate?
   - **Suggestion**: Separate JSON format but similar structure to pattern files

## File Format Example

### Tag Configuration JSON
```json
[
  {
    "name": "System Resume",
    "pattern": "resumed from STR",
    "is_regex": false,
    "icon": "🔄",
    "color": "#FFCC99",
    "enabled": true
  },
  {
    "name": "Critical Error",
    "pattern": "FATAL|CRITICAL",
    "is_regex": true,
    "icon": "⚠️",
    "color": "#FF6666",
    "enabled": true
  }
]
```

## Implementation Priority
1. **Phase 1** (Core): Tag manager, pattern matching, basic navigation
2. **Phase 2** (Enhanced): Tag list panel, multi-tag display, priority system
3. **Phase 3** (Advanced): Manual tagging, tag statistics, tag history

## Benefits
- Quick navigation to critical log points
- Reusable tag configurations across sessions
- Shareable with team members
- Works alongside search functionality
- Improves log analysis efficiency significantly

## Notes
- Keep tag limit reasonable (5-10 types) to avoid UI clutter
- Focus on pattern-based tagging initially
- Ensure performance with large log files (100k+ messages)
- Icons should be distinct and recognizable at small size
