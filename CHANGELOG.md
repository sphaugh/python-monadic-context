# Changelog

## 1.0.0

### Added

- Layers: `@layer(tag)` and `@alayer(tag)` turn a generator function into
  a factory of composable recipes for building a `Context` with resource lifecycle;
  `Layer.of`, `Layer.then`, `Layer.build`, `AsyncLayer.lift`. See README.

### Removed

- `from_dict`. A dict literal cannot carry per-entry types, so it could
  not check services against tags; use `from_pairs`.

### Changed

- `of(tag, value)` takes both arguments at once and is also available as
  `Context.of`. It was `of(tag)(value)`. A value that does not match the
  tag's type is a type error rather than widening the context's type.
- `from_pairs` (up to eight pairs) and `Context.extend` check each service
  against its tag.
- `then(ma, mb)` now returns `mb`'s value, as its type always said. It
  previously returned `ma`'s.
- `apply` evaluates the function computation before the argument.
- Generated `Tag` ids are prefixed `_anon` so they cannot equal a
  user-supplied id like `"0"`.
- `ask`, `with_service` and `requires` raise the same `KeyError` for a
  missing tag, naming it and listing the available tags.
