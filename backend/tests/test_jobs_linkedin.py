"""LinkedIn guest-HTML parsing — fixture strings, no network."""

from app.services.jobs.ats import linkedin

_SEARCH_HTML = """
<li>
  <div class="base-card job-search-card" data-entity-urn="urn:li:jobPosting:4374147499">
    <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/senior-backend-engineer-at-acme-4374147499?position=1">
      <span class="sr-only">Senior Backend Engineer</span>
    </a>
    <div class="base-search-card__info">
      <h3 class="base-search-card__title">Senior Backend Engineer</h3>
      <h4 class="base-search-card__subtitle">
        <a class="hidden-nested-link" href="https://www.linkedin.com/company/acme">Acme Corp</a>
      </h4>
      <div class="base-search-card__metadata">
        <span class="job-search-card__location">Remote, United States</span>
        <time class="job-search-card__listdate" datetime="2026-02-17">2 days ago</time>
      </div>
    </div>
  </div>
</li>
<li>
  <div class="base-card job-search-card" data-entity-urn="urn:li:jobPosting:999">
    <h3 class="base-search-card__title">Data Engineer</h3>
    <h4 class="base-search-card__subtitle"><a href="#">Beta LLC</a></h4>
    <span class="job-search-card__location">New York, NY</span>
  </div>
</li>
"""

_JD_HTML = """
<div class="description__text">
  <section class="show-more-less-html">
    <div class="show-more-less-html__markup show-more-less-html__markup--clamp-after-5">
      <strong>About the role</strong><br>We need a <b>backend</b> engineer with Python and Postgres.
    </div>
  </section>
</div>
"""


def test_card_regex_extracts_all_fields():
    cards = linkedin._CARD_RE.findall(_SEARCH_HTML)
    assert len(cards) == 2
    job_id, body = cards[0]
    assert job_id == "4374147499"
    assert linkedin._TITLE_RE.search(body).group(1).strip() == "Senior Backend Engineer"
    assert linkedin._COMPANY_RE.search(body).group(1).strip() == "Acme Corp"
    assert "Remote" in linkedin._LOCATION_RE.search(body).group(1)
    assert linkedin._DATE_RE.search(body).group(1) == "2026-02-17"


def test_jd_markup_extraction():
    match = linkedin._MARKUP_RE.search(_JD_HTML)
    assert match is not None
    from app.services.jobs.ats._util import html_to_text

    text = html_to_text(match.group(1))
    assert "backend engineer" in text.lower()
    assert "<" not in text
