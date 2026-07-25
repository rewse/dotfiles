---
name: css-standards
description: Order CSS properties outside-in following Concentric-CSS. Use this skill whenever writing, editing, or reviewing CSS, SCSS, Less, styled-components, or Tailwind @apply blocks, including when adding a single property to an existing rule, and even when the user says nothing about property order. Also use when reviewing a diff that touches stylesheets.
---

# CSS Property Order

Order the properties in every rule outside-in, following [Concentric-CSS](https://github.com/brandon-rhodes/Concentric-CSS): start with how the box is placed on the page, then work inward to its textual content. A reader learns where the element sits before learning what it looks like, so they can stop reading once they reach the part they came for.

## Group Order

1. box-sizing
2. display, position (top/right/bottom/left)
3. float, clear
4. flex
5. grid
6. align, justify
7. order, columns
8. transform
9. transition
10. visibility, opacity, z-index
11. margin
12. outline
13. border (width, style, radius, color, image, box-shadow)
14. background, cursor
15. padding
16. width (min/max), height (min/max)
17. overflow, resize
18. list-style, table-layout
19. animation
20. vertical-align
21. text (alignment, decoration, spacing)
22. color
23. font
24. content, counters
25. page breaks

For a property that is not listed, place it with the group it belongs to by function. `gap` sits with flex and grid, `filter` with transform, `caret-color` with color.

## Example

Reorder an existing rule like this. Nothing is added or removed, only moved.

Before:

```css
.box {
  color: #333;
  display: flex;
  font-size: 1rem;
  width: 100%;
  border: 1px solid;
  margin: 1rem;
  padding: 0.5rem;
  visibility: hidden;
}
```

After:

```css
.box {
  display: flex;
  visibility: hidden;
  margin: 1rem;
  border: 1px solid;
  padding: 0.5rem;
  width: 100%;
  color: #333;
  font-size: 1rem;
}
```
