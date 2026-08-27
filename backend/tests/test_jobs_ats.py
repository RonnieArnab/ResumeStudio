"""ATS response normalization — canned payloads, no network."""

from app.services.jobs.ats import ashby, greenhouse, lever, parse_board_ref


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


class _FakeClient:
    def __init__(self, routes: dict):
        self.routes = routes

    async def get(self, url, params=None):
        return _FakeResponse(self.routes[url])


async def test_greenhouse_normalizes_and_prefers_hosted_apply_url():
    client = _FakeClient(
        {
            "https://boards-api.greenhouse.io/v1/boards/acme/jobs": {
                "jobs": [
                    {
                        "id": 42,
                        "title": "Backend Engineer",
                        "absolute_url": "https://acme.com/careers/42",
                        "location": {"name": "Remote - US"},
                        "departments": [{"name": "Engineering"}],
                        "content": "&lt;p&gt;Build &amp;amp; ship&lt;/p&gt;",
                        "updated_at": "2026-01-02T00:00:00Z",
                    }
                ]
            },
            "https://boards-api.greenhouse.io/v1/boards/acme": {"name": "Acme Inc"},
        }
    )
    postings = await greenhouse.fetch_postings("acme", client)
    assert len(postings) == 1
    job = postings[0]
    assert job.id == "greenhouse:acme:42"
    assert job.company == "Acme Inc"
    assert job.remote is True
    assert job.apply_url == "https://job-boards.greenhouse.io/acme/jobs/42"
    assert "Build & ship" in job.description_text


async def test_lever_uses_plain_description_and_apply_url():
    client = _FakeClient(
        {
            "https://api.lever.co/v0/postings/acme": [
                {
                    "id": "abc-123",
                    "text": "Staff Engineer",
                    "hostedUrl": "https://jobs.lever.co/acme/abc-123",
                    "applyUrl": "https://jobs.lever.co/acme/abc-123/apply",
                    "categories": {"location": "Remote", "team": "Platform", "commitment": "Full-time"},
                    "descriptionPlain": "Own the platform.",
                    "createdAt": 1735689600000,
                }
            ]
        }
    )
    postings = await lever.fetch_postings("acme", client)
    assert postings[0].id == "lever:acme:abc-123"
    assert postings[0].apply_url.endswith("/apply")
    assert postings[0].description_text == "Own the platform."
    assert postings[0].remote is True


async def test_ashby_normalizes():
    client = _FakeClient(
        {
            "https://api.ashbyhq.com/posting-api/job-board/acme": {
                "jobs": [
                    {
                        "id": "u-1",
                        "title": "Platform Engineer",
                        "location": "Remote - EU",
                        "team": "Infra",
                        "isRemote": True,
                        "jobUrl": "https://jobs.ashbyhq.com/acme/u-1",
                        "applyUrl": "https://jobs.ashbyhq.com/acme/u-1/application",
                        "descriptionHtml": "<p>Scale things</p>",
                        "organizationName": "Acme",
                        "publishedAt": "2026-02-01T00:00:00Z",
                    }
                ]
            }
        }
    )
    postings = await ashby.fetch_postings("acme", client)
    assert postings[0].id == "ashby:acme:u-1"
    assert postings[0].company == "Acme"
    assert postings[0].apply_url.endswith("/application")
    assert postings[0].description_text == "Scale things"


def test_parse_board_ref_variants():
    assert parse_board_ref("boards.greenhouse.io/stripe") == ("greenhouse", "stripe")
    assert parse_board_ref("https://job-boards.greenhouse.io/airbnb/jobs/1") == ("greenhouse", "airbnb")
    assert parse_board_ref("jobs.lever.co/netflix") == ("lever", "netflix")
    assert parse_board_ref("ashby:openai") == ("ashby", "openai")


def test_parse_board_ref_rejects_unknown():
    import pytest

    with pytest.raises(ValueError):
        parse_board_ref("example.com/foo")
    with pytest.raises(ValueError):
        parse_board_ref("workday:ibm")
