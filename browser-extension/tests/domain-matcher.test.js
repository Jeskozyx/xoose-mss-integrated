import test from "node:test";
import assert from "node:assert/strict";

import {
  isDomainMatch,
  matchUrlAgainstRules,
  normalizeRuleDomain,
  parseTabUrl,
} from "../shared/domain-matcher.js";

const SAMPLE_RULE_SUBDOMAIN = {
  id: "konstanta-domain",
  enabled: true,
  domain: "konstantaedu.com",
  include_subdomains: true,
  schemes: ["https"],
  browsers: ["chrome", "edge", "firefox"],
};

const SAMPLE_RULE_ROOT_ONLY = {
  id: "konstanta-root-only",
  enabled: true,
  domain: "konstantaedu.com",
  include_subdomains: false,
  schemes: ["https"],
  browsers: ["chrome", "edge", "firefox"],
};

test("normalizeRuleDomain menerima domain valid dan menolak wildcard/scheme/path/port/IP", () => {
  assert.equal(normalizeRuleDomain("konstantaedu.com"), "konstantaedu.com");
  assert.equal(normalizeRuleDomain("  KONSTANTAEDU.COM. "), "konstantaedu.com");
  assert.equal(normalizeRuleDomain("sub.example.co.id"), "sub.example.co.id");

  for (const bad of [
    "",
    null,
    "*.konstantaedu.com",
    "https://konstantaedu.com",
    "konstantaedu.com/tryout",
    "konstantaedu.com:443",
    "192.168.1.1",
    "localhost",
    "bad..domain.com",
    "-bad.com",
  ]) {
    assert.equal(normalizeRuleDomain(bad), null, `Seharusnya menolak: ${String(bad)}`);
  }
});

test("Domain matcher mencocokkan root domain dan seluruh path tanpa membocorkan query/fragment", () => {
  const urls = [
    "https://konstantaedu.com",
    "https://konstantaedu.com/",
    "https://konstantaedu.com/tryout",
    "https://konstantaedu.com/ujian/123?token=secret123#section-2",
    "https://KONSTANTAEDU.COM.:443/ujian/456",
  ];

  for (const url of urls) {
    const res = matchUrlAgainstRules(url, [SAMPLE_RULE_ROOT_ONLY], "chrome");
    assert.equal(res.matched, true, `URL seharusnya cocok: ${url}`);
    assert.equal(res.rule_id, "konstanta-root-only");
    assert.equal(res.origin_domain, "konstantaedu.com");
    assert.ok(!res.origin_domain.includes("?"));
    assert.ok(!res.origin_domain.includes("#"));
    assert.ok(!res.origin_domain.includes("/"));
  }
});

test("Domain matcher menghormati include_subdomains true vs false", () => {
  const subUrls = [
    ["https://www.konstantaedu.com/tryout", "www.konstantaedu.com"],
    ["https://portal.konstantaedu.com/login", "portal.konstantaedu.com"],
    ["https://a.b.konstantaedu.com/halaman", "a.b.konstantaedu.com"],
  ];

  for (const [url, expectedHost] of subUrls) {
    const allowed = matchUrlAgainstRules(url, [SAMPLE_RULE_SUBDOMAIN], "edge");
    assert.equal(allowed.matched, true, `Subdomain seharusnya cocok saat aktif: ${url}`);
    assert.equal(allowed.origin_domain, expectedHost);

    const rejected = matchUrlAgainstRules(url, [SAMPLE_RULE_ROOT_ONLY], "edge");
    assert.equal(rejected.matched, false, `Subdomain seharusnya ditolak saat nonaktif: ${url}`);
    assert.equal(rejected.reason, "domain_mismatch");
  }
});

test("Domain matcher menolak domain mirip palsu (anti-spoofing boundary check)", () => {
  const spoofedUrls = [
    "https://konstantaedu.com.evil.com/tryout",
    "https://notkonstantaedu.com/",
    "https://fake-konstantaedu.com/ujian",
    "https://evil.com/https://konstantaedu.com",
    "https://evil.com/?next=konstantaedu.com",
  ];

  for (const url of spoofedUrls) {
    const res = matchUrlAgainstRules(url, [SAMPLE_RULE_SUBDOMAIN], "firefox");
    assert.equal(res.matched, false, `Domain palsu wajib ditolak: ${url}`);
  }
});

test("Domain matcher menolak URL invalid dan seluruh skema internal browser", () => {
  const blockedUrls = [
    "",
    "not-a-valid-url",
    "chrome://extensions/",
    "chrome://settings/",
    "chrome-extension://abcdefghijklmnop/popup.html",
    "edge://settings/profiles",
    "about:blank",
    "about:debugging#/runtime/this-firefox",
    "moz-extension://1234-5678/popup.html",
    "file:///C:/Users/test/konstantaedu.com/index.html",
    "javascript:alert(1)",
    "data:text/html,<h1>konstantaedu.com</h1>",
    "view-source:https://konstantaedu.com/",
    "http://127.0.0.1:8000/",
  ];

  for (const url of blockedUrls) {
    const parsed = parseTabUrl(url);
    assert.equal(parsed.ok, false, `parseTabUrl wajib menolak: ${url}`);
    const res = matchUrlAgainstRules(url, [SAMPLE_RULE_SUBDOMAIN], "chrome");
    assert.equal(res.matched, false, `matchUrlAgainstRules wajib menolak: ${url}`);
  }
});

test("Domain matcher memfilter scheme (default https) dan target browser per rule", () => {
  const httpRes = matchUrlAgainstRules("http://konstantaedu.com/", [SAMPLE_RULE_SUBDOMAIN], "chrome");
  assert.equal(httpRes.matched, false);

  const firefoxOnlyRule = { ...SAMPLE_RULE_SUBDOMAIN, browsers: ["firefox"] };
  assert.equal(matchUrlAgainstRules("https://konstantaedu.com/", [firefoxOnlyRule], "chrome").matched, false);
  assert.equal(matchUrlAgainstRules("https://konstantaedu.com/", [firefoxOnlyRule], "edge").matched, false);
  assert.equal(matchUrlAgainstRules("https://konstantaedu.com/", [firefoxOnlyRule], "firefox").matched, true);

  assert.equal(isDomainMatch("www.konstantaedu.com", "konstantaedu.com", true), true);
  assert.equal(isDomainMatch("konstantaedu.com.evil.com", "konstantaedu.com", true), false);
});
