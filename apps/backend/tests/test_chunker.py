"""
Tests for the document ingestion pipeline:
- app.ingestion.chunker.chunk_text
- app.ingestion.cleaner.clean_text

All tests are pure-function — no I/O, no live services.

Edge-case focus:
- Sentence-boundary awareness (never split mid-sentence)
- Overlap correctness (words from chunk N appear in chunk N+1)
- Token count accuracy
- Character position ordering
- Data completeness (no words lost)
- Degenerate inputs (empty, whitespace, no terminators, single word)
"""
import pytest

from app.ingestion.chunker import Chunk, chunk_text
from app.ingestion.cleaner import clean_text


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_sentences(n: int, words_each: int = 4, suffix: str = "covers.") -> str:
    """Build a predictable text with n sentences of `words_each` words."""
    sentences = [" ".join([f"word{i}w{j}" for j in range(words_each)]) + f" {suffix}" for i in range(n)]
    return " ".join(sentences)


# ─────────────────────────────────────────────────────────────────────────────
# TestChunkText
# ─────────────────────────────────────────────────────────────────────────────

class TestChunkText:

    # ── Degenerate inputs ─────────────────────────────────────────────────────

    def test_empty_string_returns_empty_list(self):
        assert chunk_text("") == []

    def test_whitespace_only_returns_empty_list(self):
        assert chunk_text("   \n\n\t  ") == []

    def test_single_short_sentence(self):
        chunks = chunk_text("This policy covers diabetes treatment.")
        assert len(chunks) == 1

    def test_single_word_with_period(self):
        chunks = chunk_text("Hello.")
        assert len(chunks) == 1
        assert "Hello." in chunks[0].text

    def test_text_shorter_than_max_words_is_one_chunk(self):
        text = "First sentence here. Second sentence there. Third one done."
        chunks = chunk_text(text, max_words=100)
        assert len(chunks) == 1

    # ── Chunk count and multi-chunk behaviour ─────────────────────────────────

    def test_long_text_produces_multiple_chunks(self):
        text = _build_sentences(50, words_each=5)
        chunks = chunk_text(text, max_words=20, overlap_words=0)
        assert len(chunks) > 1

    def test_very_small_max_words_many_chunks(self):
        text = _build_sentences(30, words_each=3)
        chunks = chunk_text(text, max_words=6, overlap_words=0)
        assert len(chunks) >= 5

    # ── Sentence-boundary awareness ───────────────────────────────────────────

    def test_never_splits_mid_sentence(self):
        """Each sentence is 5 words; max_words=8 can only hold one sentence at a time.
        Chunks must align on sentence boundaries."""
        sentences = [
            "Coverage includes hospitalisation expenses fully.",
            "Waiting period applies to diabetes treatment.",
            "Premium varies based on age band.",
            "OPD consultations are reimbursed separately.",
        ]
        text = " ".join(sentences)
        chunks = chunk_text(text, max_words=8, overlap_words=0)
        # Each sentence must appear whole in exactly one chunk
        for sentence in sentences:
            appears_in = [c for c in chunks if sentence in c.text]
            assert len(appears_in) >= 1, f"Sentence not found in any chunk: {sentence}"

    def test_text_without_sentence_terminators_is_one_chunk(self):
        """No periods/!/? → treated as one sentence → always one chunk regardless of max_words."""
        text = "this is a very long run on sentence without any terminators at all"
        chunks = chunk_text(text, max_words=3, overlap_words=0)
        assert len(chunks) == 1

    # ── Overlap correctness ───────────────────────────────────────────────────

    def test_overlap_words_appear_in_next_chunk(self):
        """The tail of chunk N must appear at the head of chunk N+1."""
        text = _build_sentences(30, words_each=4)
        overlap = 5
        chunks = chunk_text(text, max_words=16, overlap_words=overlap)

        if len(chunks) < 2:
            pytest.skip("Not enough text to produce multiple chunks")

        last_words_of_chunk0 = chunks[0].text.split()[-overlap:]
        first_words_of_chunk1 = chunks[1].text.split()[:overlap]
        assert last_words_of_chunk0 == first_words_of_chunk1

    def test_zero_overlap_chunks_have_no_repeated_unique_sentences(self):
        """With overlap=0, a unique sentence should not appear in two consecutive chunks."""
        sentences = [
            "Policy A covers diabetes.",
            "Policy B covers hypertension.",
            "Policy C covers maternity.",
            "Policy D covers cancer.",
            "Policy E covers accident.",
        ]
        text = " ".join(sentences)
        chunks = chunk_text(text, max_words=6, overlap_words=0)
        # Build dict: sentence → list of chunk indices it appears in
        coverage = {s: [i for i, c in enumerate(chunks) if s in c.text] for s in sentences}
        for sent, indices in coverage.items():
            # With no overlap, a sentence should appear in at most one chunk
            # (unless the sentence itself is longer than max_words, which it isn't here)
            assert len(indices) <= 1, f"Sentence '{sent}' appears in multiple chunks: {indices}"

    # ── Metadata correctness ──────────────────────────────────────────────────

    def test_chunk_indices_are_monotonically_increasing(self):
        text = _build_sentences(40, words_each=4)
        chunks = chunk_text(text, max_words=15)
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    def test_token_count_equals_actual_word_count(self):
        text = "This covers hospitalisation. And also OPD visits. Premium is low."
        chunks = chunk_text(text, max_words=100)
        for chunk in chunks:
            assert chunk.token_count == len(chunk.text.split())

    def test_char_start_is_non_negative(self):
        text = "First sentence. Second sentence. Third sentence."
        for chunk in chunk_text(text):
            assert chunk.char_start >= 0

    def test_char_end_greater_than_char_start(self):
        text = "First sentence. Second sentence."
        for chunk in chunk_text(text):
            assert chunk.char_end > chunk.char_start

    def test_chunks_are_frozen_dataclasses(self):
        chunks = chunk_text("A sentence here.")
        chunk = chunks[0]
        with pytest.raises((TypeError, AttributeError)):
            chunk.text = "modified"  # type: ignore[misc]

    # ── Data completeness — no word loss ─────────────────────────────────────

    def test_all_source_words_present_in_at_least_one_chunk(self):
        """Union of all chunk words must be a superset of source words.
        With overlap, some words appear in multiple chunks — that's expected."""
        sentences = [
            "Coverage includes hospitalisation.",
            "Pre-existing conditions need waiting period.",
            "Premium slab depends on city tier.",
        ]
        text = " ".join(sentences)
        chunks = chunk_text(text, max_words=10, overlap_words=3)

        all_chunk_words: set[str] = set()
        for c in chunks:
            all_chunk_words.update(c.text.split())

        original_words = set(text.split())
        assert original_words.issubset(all_chunk_words), (
            f"Missing words: {original_words - all_chunk_words}"
        )

    # ── max_words boundary behaviour ─────────────────────────────────────────

    def test_exactly_max_words_text_produces_one_chunk(self):
        """Text whose word count equals max_words but is a single sentence → 1 chunk."""
        words = " ".join(["word"] * 10) + "."
        chunks = chunk_text(words, max_words=10, overlap_words=0)
        assert len(chunks) == 1

    def test_chunk_token_count_never_far_exceeds_max_words(self):
        """A chunk may exceed max_words by at most one sentence's worth of words,
        because we flush BEFORE adding the sentence that would overflow."""
        sentence_len = 6
        text = _build_sentences(50, words_each=sentence_len)
        max_w = 20
        chunks = chunk_text(text, max_words=max_w, overlap_words=0)
        for chunk in chunks[:-1]:  # last chunk may be a remainder
            # The chunk was emitted BEFORE a sentence that would push it over.
            # So chunk.token_count <= max_words + one_sentence_worth
            assert chunk.token_count <= max_w + sentence_len + 5  # 5 for tolerance


# ─────────────────────────────────────────────────────────────────────────────
# TestCleanText
# ─────────────────────────────────────────────────────────────────────────────

class TestCleanText:

    # ── Degenerate inputs ─────────────────────────────────────────────────────

    def test_empty_string_returns_empty(self):
        assert clean_text("") == ""

    def test_whitespace_only_returns_empty(self):
        assert clean_text("   \n\n\t  ") == ""

    def test_normal_text_passes_through_unchanged(self):
        text = "This policy covers hospitalisation up to five lakhs."
        assert clean_text(text) == text

    # ── Unicode normalisation ─────────────────────────────────────────────────

    def test_fi_ligature_normalised_to_two_chars(self):
        # U+FB01 (ﬁ) is the fi ligature — NFKC normalises it to 'fi'
        assert clean_text("ﬁrst") == "first"

    def test_fullwidth_digits_normalised(self):
        # U+FF11 (１) is fullwidth 1 — NFKC normalises to '1'
        assert clean_text("Sum insured １０ lakhs") == "Sum insured 10 lakhs"

    def test_non_breaking_space_normalised(self):
        # Non-breaking space U+00A0 → regular space after NFKC
        result = clean_text("coverage includes")
        assert " " not in result

    # ── Control character removal ─────────────────────────────────────────────

    def test_null_byte_removed(self):
        result = clean_text("normal\x00text")
        assert "\x00" not in result
        assert "normal" in result
        assert "text" in result

    def test_form_feed_removed(self):
        result = clean_text("page one\x0cpage two")
        assert "\x0c" not in result

    def test_printable_chars_preserved(self):
        text = "Coverage: ₹5,00,000 for hospitalisation."
        result = clean_text(text)
        assert "5,00,000" in result

    # ── Repeated-line removal (headers/footers) ───────────────────────────────

    def test_line_appearing_3_times_is_removed(self):
        header = "AarogyaShield Policy Document"
        text = "\n".join([header] * 3 + ["Actual policy content here."])
        result = clean_text(text)
        assert header not in result
        assert "Actual policy content" in result

    def test_line_appearing_exactly_2_times_is_kept(self):
        """Threshold is 3 — lines appearing twice are not removed."""
        line = "Page Footer"
        text = f"{line}\nSome content.\n{line}\nMore content."
        result = clean_text(text)
        assert line in result

    def test_unique_lines_always_kept(self):
        text = "Line one.\nLine two.\nLine three."
        result = clean_text(text)
        assert "Line one" in result
        assert "Line two" in result
        assert "Line three" in result

    def test_empty_lines_not_counted_as_repeated(self):
        """Blank lines should not trigger the repeated-line removal."""
        text = "\n\nSome content.\n\nMore content.\n\n"
        result = clean_text(text)
        assert "Some content" in result
        assert "More content" in result

    # ── Blank-line collapse ───────────────────────────────────────────────────

    def test_three_consecutive_blank_lines_collapsed(self):
        text = "Paragraph one.\n\n\n\nParagraph two."
        result = clean_text(text)
        assert "\n\n\n" not in result

    def test_two_blank_lines_preserved(self):
        text = "Paragraph one.\n\nParagraph two."
        result = clean_text(text)
        assert "\n\n" in result

    # ── Horizontal whitespace collapse ────────────────────────────────────────

    def test_multiple_spaces_collapsed_to_one(self):
        result = clean_text("Word1   Word2    Word3")
        assert "  " not in result
        assert "Word1 Word2 Word3" in result

    def test_tabs_collapsed_to_space(self):
        result = clean_text("Column1\t\tColumn2")
        assert "\t" not in result

    # ── Strip leading/trailing whitespace ─────────────────────────────────────

    def test_result_stripped(self):
        text = "  \n  Some content here.  \n  "
        result = clean_text(text)
        assert result == result.strip()
        assert result != ""

    # ── Combined pipeline ─────────────────────────────────────────────────────

    def test_full_pipeline_on_realistic_text(self):
        """Simulates a PDF with unicode, control chars, repeated headers, and multi-spaces."""
        header = "AarogyaShield – Policy Brochure"
        content = "\n".join([
            header,
            "Coverage Details",
            header,
            "\x00",
            "Sum Insured: ﬁve   lakhs",
            header,
            "Waiting period: 2 years.",
            "",
        ])
        result = clean_text(content)
        assert header not in result          # removed (3 occurrences)
        assert "\x00" not in result          # control char removed
        assert "five" in result              # ﬁ→fi normalised, spaces collapsed
        assert "Waiting period: 2 years." in result
        assert "  " not in result            # no double spaces remain
