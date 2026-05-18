# Debian Packaging Notes

This note records packaging-related decisions and constraints that matter if the
PyQt6 port is eventually prepared for upload to Debian.

## File Format Support And Debian Main

Supporting a proprietary or vendor-specific file format does not by itself block
upload to the Debian `main` archive.

What Debian primarily evaluates is:

- whether the packaged software itself is DFSG-free;
- whether its runtime and build dependencies are DFSG-free;
- whether bundled data, examples, icons, documentation, and test fixtures are
  redistributable under Debian-acceptable terms;
- whether the implementation introduces patent or license problems that would
  prevent inclusion in `main`.

Because of that, a program in Debian may support formats such as MP3, AAC, or
 vendor-specific document/audio formats without becoming non-free simply because
it can open those files.

## What This Means For WRK Support

If `dmidiplayer` eventually supports Cakewalk `.wrk` files, that should not by
itself create a Debian archive problem, provided that:

- the parser implementation is written as free software or derived from
  DFSG-free source material;
- the project does not depend on a non-free SDK, library, or binary blob to
  provide WRK support;
- any bundled WRK sample files or regression fixtures are redistributable;
- any imported specification text, comments, or sample material used during
  implementation is compatible with Debian `main`.

In other words, the key issue is not "does the program open a proprietary
format?" but rather "is the shipped code and data free enough for Debian
`main`?"

## Practical Risks To Watch

The areas most likely to cause trouble are:

1. copying code or specification text from a non-free source;
2. bundling non-redistributable example files for tests or demos;
3. adding a dependency on a non-free parser library or SDK;
4. shipping assets or documentation without clear redistribution rights;
5. introducing patent-sensitive code without checking the implementation path.

## Safe Direction For This Repository

For this project, the Debian-friendly path is:

- keep parser code in this repository under GPL-compatible terms;
- generate or author test fixtures ourselves when possible;
- document provenance and licensing clearly in `debian/copyright` when Debian
  packaging begins;
- avoid any dependency on proprietary components for format support.

## Useful Debian References

- Debian Social Contract / DFSG:
  <https://www.debian.org/social_contract.en.html>
- Debian Policy, archive and copyright considerations:
  <https://www.debian.org/doc/debian-policy/ch-archive.html>
- Debian legal license guidance:
  <https://www.debian.org/legal/licenses/>
- Machine-readable `debian/copyright` format:
  <https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/>
- Debian wiki page showing support for formats such as MP3/AAC in Debian tools:
  <https://wiki.debian.org/SoundFormats>

## Current Conclusion

Planned `.wrk` support is compatible with a future Debian upload as long as the
implementation, dependencies, and bundled data remain DFSG-free and
redistributable.
