---
inclusion: fileMatch
fileMatchPattern: "**/*.css"
---

# CSS Standards

Follow [Concentric-CSS](https://github.com/brandon-rhodes/Concentric-CSS) for CSS property ordering. Properties are ordered outside-in, from how the box is placed to its textual content.

## Property Group Order

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

### Do

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

### Don't

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
