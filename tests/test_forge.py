import os
import time
import types
import pytest
from mdf_forge import forge
from mdf_forge import toolbox


# Manually logging in for Query testing
query_search_client = toolbox.login(credentials={"app_name": "MDF_Forge", "services": ["search"], "index": "mdf"})["search"]


############################
# Query tests
############################
def test_query_term():
    q = forge.Query(query_search_client)
    # Single match test
    assert isinstance(q.term("term1"), forge.Query)
    assert q.query == "(term1"
    assert q.initialized == True
    # Multi-match test
    q.and_join().term("term2")
    assert q.query == "(term1 AND term2"
    # Grouping test
    q.or_join(close_group=True).term("term3")
    assert q.query == "(term1 AND term2) OR (term3"


def test_query_field():
    q = forge.Query(query_search_client)
    # Single field and return value test
    assert isinstance(q.field("mdf.source_name", "oqmd"), forge.Query)
    assert q.query == "(mdf.source_name:oqmd"
    # Multi-field and grouping test
    q.and_join(close_group=True).field("dc.title", "sample")
    assert q.query == "(mdf.source_name:oqmd) AND (dc.title:sample"
    # Negation test
    q.negate()
    assert q.query == "(mdf.source_name:oqmd) AND (dc.title:sample NOT "
    # Explicit operator test
    # Makes invalid query for this case
    q.operator("NOT")
    assert q.query == "(mdf.source_name:oqmd) AND (dc.title:sample NOT  NOT "
    # Ensure advanced is set
    assert q.advanced


def test_query_search(capsys):
    # Error on no query
    q1 = forge.Query(query_search_client)
    assert q1.search() == []
    out, err = capsys.readouterr()
    assert "Error: No query specified" in out

    # Return info if requested
    q2 = forge.Query(query_search_client)
    res2 = q2.search(q="Al", info=False)
    assert isinstance(res2, list)
    assert isinstance(res2[0], dict)
    q3 = forge.Query(query_search_client)
    res3 = q3.search(q="Al", info=True)
    assert isinstance(res3, tuple)
    assert isinstance(res3[0], list)
    assert isinstance(res3[0][0], dict)
    assert isinstance(res3[1], dict)

    # Check limit
    q4 = forge.Query(query_search_client)
    res4 = q4.search("oqmd", limit=3)
    assert len(res4) == 3


def test_query_aggregate():
    q = forge.Query(query_search_client)
    r = q.aggregate('mdf.source_name:oqmd AND '
                        '(oqmd.configuration:static OR oqmd.configuration:standard) '
                        'AND oqmd.converged:True AND oqmd.band_gap.value:>2')
    assert isinstance(r[0], dict)


def test_query_chaining():
    q1 = forge.Query(query_search_client)
    q1.field("source_name", "cip")
    q1.and_join()
    q1.field("elements", "Al")
    res1 = q1.search(limit=10000)
    res2 = forge.Query(query_search_client).field("source_name", "cip").and_join().field("elements", "Al").search(limit=10000)
    assert all([r in res2 for r in res1]) and all([r in res1 for r in res2])


############################
# Forge tests
############################

# Sample results for download testing
example_result1 = [{
        'mdf': {
            'links': {
                'landing_page': 'https://data.materialsdatafacility.org/test/test_fetch.txt',
                'txt': {
                    'globus_endpoint': '82f1b5c6-6e9b-11e5-ba47-22000b92c6ec',
                    'http_host': 'https://data.materialsdatafacility.org',
                    'path': '/test/test_fetch.txt'
                }
            }
        }
    }]
example_result2 = [{
        'mdf': {
            'links': {
                'landing_page': 'https://data.materialsdatafacility.org/test/test_fetch.txt',
                'txt': {
                    'globus_endpoint': '82f1b5c6-6e9b-11e5-ba47-22000b92c6ec',
                    'http_host': 'https://data.materialsdatafacility.org',
                    'path': '/test/test_fetch.txt'
                }
            }
        }
    }, {
        'mdf': {
            'links': {
                'landing_page': 'https://data.materialsdatafacility.org/test/test_multifetch.txt',
                'txt': {
                    'globus_endpoint': '82f1b5c6-6e9b-11e5-ba47-22000b92c6ec',
                    'http_host': 'https://data.materialsdatafacility.org',
                    'path': '/test/test_multifetch.txt'
                }
            }
        }
    }]


# Helper
# Field can be "mdf.elements" or "mdf.source_name"
# Return codes:
#  -1: No match, the value was never found
#   0: Exclusive match, no values other than argument found
#   1: Inclusive match, some values other than argument found
#   2: Partial match, value is found in some but not all results
def check_field(res, field, value):
    supported_fields = ["mdf.elements", "mdf.source_name"]
    if field not in supported_fields:
        raise ValueError("Implement or re-spell " + field + "because check_field only works on " + str(supported_fields))
    # If no results, set matches to false
    all_match = (len(res) > 0)
    only_match = (len(res) > 0)
    some_match = False
    for r in res:
        if field == "mdf.elements":
            try:
                vals = r["mdf"]["elements"]
            except KeyError:
                vals = []
        elif field == "mdf.source_name":
            vals = [r["mdf"]["source_name"]]
        # If a result does not contain the value, no match
        if value not in vals:
            all_match = False
            only_match = False
        # If a result contains other values, inclusive match
        elif len(vals) != 1:
            only_match = False
            some_match = True
        else:
            some_match = True

    if only_match:
        #print("Exclusive match")
        return 0
    elif all_match:
        #print("Inclusive match")
        return 1
    elif some_match:
        #print("Partial match")
        return 2
    else:
        #print("No match")
        return -1


def test_forge_match_field():
    f1 = forge.Forge()
    # Basic usage
    f1.match_field("mdf.source_name", "nist_janaf")
    res1 = f1.search()
    assert check_field(res1, "mdf.source_name", "nist_janaf") == 0
    # Check that query clears
    assert f1.search() == []
    # Also checking check_field
    f2 = forge.Forge()
    f2.match_field("mdf.elements", "Al")
    res2 = f2.search()
    assert check_field(res2, "mdf.elements", "Al") == 1


def test_forge_exclude_field():
    f1 = forge.Forge()
    # Basic usage
    f1.exclude_field("mdf.elements", "Al")
    f1.match_field("mdf.source_name", "core_mof")
    res1 = f1.search()
    assert check_field(res1, "mdf.elements", "Al") == -1


def test_forge_match_range():
    # Single-value use
    f1 = forge.Forge()
    f1.match_range("mdf.elements", "Al", "Al")
    res1, info1 = f1.search(info=True)
    assert check_field(res1, "mdf.elements", "Al") == 1
    f2 = forge.Forge()
    res2, info2 = f2.search("mdf.elements:Al", advanced=True, info=True)
    assert info1["total_query_matches"] == info2["total_query_matches"]
    # Non-matching use, test inclusive
    f3 = forge.Forge()
    f3.match_range("mdf.elements", "Al", "Al", inclusive=False)
    assert f3.search() == []
    # Actual range
    f4 = forge.Forge()
    f4.match_range("mdf.elements", "Al", "Cu")
    res4, info4 = f4.search(info=True)
    assert info1["total_query_matches"] < info4["total_query_matches"]
    assert (check_field(res4, "mdf.elements", "Al") >= 0 or
            check_field(res4, "mdf.elements", "Cu") >= 0)


def test_forge_exclude_range():
    # Single-value use
    f1 = forge.Forge()
    f1.exclude_range("mdf.elements", "Am", "*")
    f1.exclude_range("mdf.elements", "*", "Ak")
    res1, info1 = f1.search(info=True)
    assert (check_field(res1, "mdf.elements", "Al") == 0 or
            check_field(res1, "mdf.elements", "Al") == 2)
    f2 = forge.Forge()
    res2, info2 = f2.search("mdf.elements:Al", advanced=True, info=True)
    assert info1["total_query_matches"] <= info2["total_query_matches"]
    # Non-matching use, test inclusive
    f3 = forge.Forge()
    f3.exclude_range("mdf.elements", "Am", "*")
    f3.exclude_range("mdf.elements", "*", "Ak")
    f3.exclude_range("mdf.elements", "Al", "Al", inclusive=False)
    res3, info3 = f3.search(info=True)
    assert info1["total_query_matches"] == info3["total_query_matches"]


def test_forge_exclusive_match():
    f1 = forge.Forge()
    f1.exclusive_match("mdf.elements", "Al")
    res1 = f1.search()
    assert check_field(res1, "mdf.elements", "Al") == 0
    f2 = forge.Forge()
    f2.exclusive_match("mdf.elements", ["Al", "Cu"])
    res2 = f2.search()
    assert check_field(res2, "mdf.elements", "Al") == 1
    assert check_field(res2, "mdf.elements", "Cu") == 1
    assert check_field(res2, "mdf.elements", "Cp") == -1
    assert check_field(res2, "mdf.elements", "Fe") == -1


def test_forge_match_sources():
    f1 = forge.Forge()
    # One source
    f1.match_sources("nist_janaf")
    res1 = f1.search()
    assert res1 != []
    assert check_field(res1, "mdf.source_name", "nist_janaf") == 0
    # Multi-source
    f2 = forge.Forge()
    f2.match_sources(["nist_janaf", "hopv"])
    res2 = f2.search()
    # res1 is a subset of res2
    assert len(res2) > len(res1)
    assert all([r1 in res2 for r1 in res1])
    assert check_field(res2, "mdf.source_name", "nist_janaf") == 2


def test_forge_match_elements():
    f1 = forge.Forge()
    # One element
    f1.match_elements("Al")
    res1 = f1.search()
    assert res1 != []
    check_val1 = check_field(res1, "mdf.elements", "Al")
    assert check_val1 == 0 or check_val1 == 1
    # Multi-element
    f2 = forge.Forge()
    f2.match_elements(["Al", "Cu"])
    res2 = f2.search()
    assert check_field(res2, "mdf.elements", "Al") == 1
    assert check_field(res2, "mdf.elements", "Cu") == 1


def test_forge_search(capsys):
    # Error on no query
    f1 = forge.Forge()
    assert f1.search() == []
    out, err = capsys.readouterr()
    assert "Error: No query specified" in out

    # Return info if requested
    f2 = forge.Forge()
    res2 = f2.search(q="Al", info=False)
    assert isinstance(res2, list)
    assert isinstance(res2[0], dict)
    f3 = forge.Forge()
    res3 = f3.search(q="Al", info=True)
    assert isinstance(res3, tuple)
    assert isinstance(res3[0], list)
    assert isinstance(res3[0][0], dict)
    assert isinstance(res3[1], dict)

    # Check limit
    f4 = forge.Forge()
    res4 = f4.search("oqmd", limit=3)
    assert len(res4) == 3


def test_forge_search_by_elements():
    f1 = forge.Forge()
    f2 = forge.Forge()
    elements = ["Cu", "Al"]
    sources = ["oqmd", "nist_xps_db"]
    res1, info1 = f1.match_sources(sources).match_elements(elements).search(limit=10000, info=True)
    res2, info2 = f2.search_by_elements(elements, sources, limit=10000, info=True)
    assert all([r in res2 for r in res1]) and all([r in res1 for r in res2])
    assert check_field(res1, "mdf.elements", "Al") == 1
    assert check_field(res1, "mdf.source_name", "oqmd") == 2


def test_forge_aggregate_source():
    # Test limit
    f1 = forge.Forge()
    res1 = f1.aggregate_source("amcs")
    assert isinstance(res1, list)
    assert len(res1) > 10000
    assert isinstance(res1[0], dict)


def test_forge_aggregate():
    f = forge.Forge()
    r = f.aggregate('mdf.source_name:oqmd AND '
                        '(oqmd.configuration:static OR oqmd.configuration:standard) '
                        'AND oqmd.converged:True AND oqmd.band_gap.value:>2')
    assert isinstance(r[0], dict)


def test_forge_reset_query():
    f = forge.Forge()
    # Term will return results
    f.match_field("elements", "Al")
    f.reset_query()
    # Specifying no query will return no results
    assert f.search() == []


def test_forge_http_download():
    f = forge.Forge()
    # Simple case
    f.http_download(example_result1)
    assert os.path.exists("./test_fetch.txt")
    os.remove("./test_fetch.txt")
    # With dest and preserve_dir
    dest_path = os.path.expanduser("~/mdf")
    f.http_download(example_result1, dest=dest_path, preserve_dir=True)
    assert os.path.exists(os.path.join(dest_path, "test", "test_fetch.txt"))
    os.remove(os.path.join(dest_path, "test", "test_fetch.txt"))
    os.rmdir(os.path.join(dest_path, "test"))
    # With multiple files
    f.http_download(example_result2, dest=dest_path)
    assert os.path.exists(os.path.join(dest_path, "test_fetch.txt"))
    assert os.path.exists(os.path.join(dest_path, "test_multifetch.txt"))
    os.remove(os.path.join(dest_path, "test_fetch.txt"))
    os.remove(os.path.join(dest_path, "test_multifetch.txt"))


@pytest.mark.xfail(reason="Test relies on get_local_ep() which will cause failures if exactly one EP isn't detected.")
def test_forge_globus_download():
    f = forge.Forge()
    # Simple case
    res1 = f.globus_download(example_result1)
    assert os.path.exists("./test_fetch.txt")
    os.remove("./test_fetch.txt")
    # With dest and preserve_dir
    dest_path = os.path.expanduser("~/mdf")
    f.globus_download(example_result1, dest=dest_path, preserve_dir=True)
    assert os.path.exists(os.path.join(dest_path, "test", "test_fetch.txt"))
    os.remove(os.path.join(dest_path, "test", "test_fetch.txt"))
    os.rmdir(os.path.join(dest_path, "test"))
    # With multiple files
    f.globus_download(example_result2, dest=dest_path)
    assert os.path.exists(os.path.join(dest_path, "test_fetch.txt"))
    assert os.path.exists(os.path.join(dest_path, "test_multifetch.txt"))
    os.remove(os.path.join(dest_path, "test_fetch.txt"))
    os.remove(os.path.join(dest_path, "test_multifetch.txt"))


def test_forge_http_stream():
    f = forge.Forge()
    # Simple case
    res1 = f.http_stream(example_result1)
    assert isinstance(res1, types.GeneratorType)
    assert next(res1) == "This is a test document for Forge testing. Please do not remove.\n"
    # With multiple files
    res2 = f.http_stream(example_result2)
    assert isinstance(res2, types.GeneratorType)
    assert next(res2) == "This is a test document for Forge testing. Please do not remove.\n"
    assert next(res2) == "This is a second test document for Forge testing. Please do not remove.\n"


def test_forge_http_return():
    f = forge.Forge()
    # Simple case
    res1 = f.http_return(example_result1)
    assert isinstance(res1, list)
    assert res1 == ["This is a test document for Forge testing. Please do not remove.\n"]
    # With multiple files
    res2 = f.http_return(example_result2)
    assert isinstance(res2, list)
    assert res2 == ["This is a test document for Forge testing. Please do not remove.\n", "This is a second test document for Forge testing. Please do not remove.\n"]


def test_forge_chaining():
    f1 = forge.Forge()
    f1.match_field("source_name", "cip")
    f1.match_field("elements", "Al")
    res1 = f1.search()
    res2 = forge.Forge().match_field("source_name", "cip").match_field("elements", "Al").search()
    assert all([r in res2 for r in res1]) and all([r in res1 for r in res2])


def test_forge_show_fields():
    f1 = forge.Forge()
    res1 = f1.show_fields()
    assert "mdf" in res1.keys()
    res2 = f1.show_fields("mdf")
    assert "mdf.mdf_id" in res2.keys()

