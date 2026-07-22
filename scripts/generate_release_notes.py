#!/usr/bin/env python3
"""Generate git-backed release notes for the docs site."""

from __future__ import annotations

import argparse
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
TAG_SPLIT = "\x1f"
COMMIT_SPLIT = "\x1f"


@dataclass(frozen=True)
class TagInfo:
    name: str
    date: str
    headline: str
    detail: str | None


@dataclass(frozen=True)
class CommitInfo:
    sha: str
    subject: str


def run_git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_tags(repo_root: Path) -> list[TagInfo]:
    output = run_git(
        repo_root,
        "for-each-ref",
        "--sort=version:refname",
        f"--format=%(refname:short){TAG_SPLIT}%(creatordate:short){TAG_SPLIT}%(subject)",
        "refs/tags",
    )
    if not output:
        return []

    tags = []
    for line in output.splitlines():
        name, date, headline = line.split(TAG_SPLIT, 2)
        tags.append(
            TagInfo(
                name=name,
                date=date,
                headline=headline.strip(),
                detail=get_tag_detail(repo_root, name),
            )
        )
    return tags


def get_tag_detail(repo_root: Path, tag_name: str) -> str | None:
    body = run_git(repo_root, "log", "-1", "--format=%B", tag_name)
    raw_lines = [line.strip() for line in body.splitlines()]
    if not raw_lines:
        return None

    subject = raw_lines[0]
    paragraph: list[str] = []
    started = False

    for line in raw_lines[1:]:
        if not line:
            if started:
                break
            continue
        if line == subject:
            continue
        started = True
        paragraph.append(line)

    if paragraph:
        return " ".join(paragraph)
    return None


def get_commit_subjects(repo_root: Path, revision_range: str) -> list[CommitInfo]:
    output = run_git(
        repo_root,
        "log",
        "--reverse",
        f"--format=%H{COMMIT_SPLIT}%s",
        revision_range,
    )
    if not output:
        return []

    commits = []
    for line in output.splitlines():
        sha, subject = line.split(COMMIT_SPLIT, 1)
        commits.append(CommitInfo(sha=sha, subject=subject.strip()))
    return commits


def get_changed_files(repo_root: Path, start_ref: str, end_ref: str) -> list[str]:
    output = run_git(repo_root, "diff", "--name-only", start_ref, end_ref)
    return [line for line in output.splitlines() if line]


def current_head_tag(repo_root: Path) -> str | None:
    try:
        return run_git(repo_root, "describe", "--tags", "--exact-match")
    except subprocess.CalledProcessError:
        return None


def classify_commit(subject: str) -> str:
    match = re.match(r"([A-Za-z0-9_-]+)(?:\([^)]+\))?!?:", subject)
    if match:
        return match.group(1).lower()
    if subject.lower().startswith("merge pull request"):
        return "merge"
    return "other"


def area_for_path(path: str) -> str:
    parts = Path(path).parts
    if not parts:
        return "(root)"
    if parts[0] in {"uniqc", "docs", "examples", "UniqcCpp", ".github"}:
        return "/".join(parts[:2]) if len(parts) > 1 and parts[0] == "uniqc" else parts[0]
    return parts[0]


def summarize_categories(commits: list[CommitInfo]) -> Counter[str]:
    return Counter(classify_commit(commit.subject) for commit in commits)


def summarize_areas(files: list[str]) -> Counter[str]:
    return Counter(area_for_path(path) for path in files)


def format_category_table(counter: Counter[str]) -> list[str]:
    if not counter:
        return ["无。", ""]

    lines = ["| 类型 | 数量 |", "| --- | ---: |"]
    for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| `{name}` | {count} |")
    lines.append("")
    return lines


def format_area_list(counter: Counter[str]) -> list[str]:
    if not counter:
        return ["无。", ""]

    lines = []
    for area, count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- `{area}`: {count} 个文件")
    lines.append("")
    return lines


def format_commit_list(commits: list[CommitInfo]) -> list[str]:
    if not commits:
        return ["无。", ""]

    lines = []
    for commit in commits:
        lines.append(f"- `{commit.sha[:7]}` {commit.subject}")
    lines.append("")
    return lines


def build_release_section(
    tag: TagInfo,
    previous_tag: TagInfo | None,
    repo_root: Path,
) -> list[str]:
    if previous_tag is None:
        compare_label = f"repo start -> {tag.name}"
        commit_range = tag.name
        files = get_changed_files(repo_root, EMPTY_TREE, tag.name)
    else:
        compare_label = f"{previous_tag.name}..{tag.name}"
        commit_range = f"{previous_tag.name}..{tag.name}"
        files = get_changed_files(repo_root, previous_tag.name, tag.name)

    commits = get_commit_subjects(repo_root, commit_range)
    category_counts = summarize_categories(commits)
    area_counts = summarize_areas(files)

    lines = [
        f"## {tag.name}",
        "",
        f"- 发布日期：`{tag.date}`",
        f"- 发布标题：{tag.headline}",
        *( [f"- 补充说明：{tag.detail}"] if tag.detail else [] ),
        f"- 对比区间：`{compare_label}`",
        f"- 提交数：{len(commits)}",
        f"- 变更文件数：{len(files)}",
        "",
        "### 提交类型统计",
        "",
        *format_category_table(category_counts),
        "### 变更区域",
        "",
        *format_area_list(area_counts),
        "### 提交列表",
        "",
        *format_commit_list(commits),
    ]
    return lines


def build_unreleased_section(repo_root: Path, latest_tag: TagInfo | None) -> list[str]:
    if latest_tag is None:
        commits = get_commit_subjects(repo_root, "HEAD")
        files = get_changed_files(repo_root, EMPTY_TREE, "HEAD")
        compare_label = "repo start -> HEAD"
    else:
        if current_head_tag(repo_root) == latest_tag.name:
            return []
        commits = get_commit_subjects(repo_root, f"{latest_tag.name}..HEAD")
        files = get_changed_files(repo_root, latest_tag.name, "HEAD")
        compare_label = f"{latest_tag.name}..HEAD"

    category_counts = summarize_categories(commits)
    area_counts = summarize_areas(files)

    lines = [
        "## 开发中变更",
        "",
        "- 说明：这一节展示自最新 tag 之后、当前 `HEAD` 上尚未形成新版本的变更。",
        f"- 对比区间：`{compare_label}`",
        f"- 提交数：{len(commits)}",
        f"- 变更文件数：{len(files)}",
        "",
        "### 提交类型统计",
        "",
        *format_category_table(category_counts),
        "### 变更区域",
        "",
        *format_area_list(area_counts),
        "### 提交列表",
        "",
        *format_commit_list(commits),
    ]
    return lines


def build_overview(tags: list[TagInfo], repo_root: Path) -> list[str]:
    lines = [
        "## 详细变更记录（自动整理）",
        "",
        "这一节会在文档构建时根据当前仓库的 `git tag`、提交标题与变更文件路径整理生成。",
        "这里主要提供可核对的版本变化记录；兼容性判断和升级建议以上面的说明为准。",
        "",
    ]

    if not tags:
        lines.extend(
            [
                "当前仓库还没有发现 tag，因此没有可展示的正式版本历史。",
                "",
            ]
        )
        return lines

    lines.extend(
        [
            "### 版本总览",
            "",
            "| 版本 | 日期 | 标题 |",
            "| --- | --- | --- |",
        ]
    )
    for tag in reversed(tags):
        lines.append(f"| `{tag.name}` | `{tag.date}` | {tag.headline} |")
    lines.append("")

    unreleased = build_unreleased_section(repo_root, tags[-1])
    if unreleased:
        lines.extend(unreleased)

    for index in range(len(tags) - 1, -1, -1):
        tag = tags[index]
        previous_tag = tags[index - 1] if index > 0 else None
        lines.extend(build_release_section(tag, previous_tag, repo_root))

    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root containing the git history.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Markdown output path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_path = args.output.resolve()

    tags = get_tags(repo_root)
    markdown = "\n".join(build_overview(tags, repo_root)).rstrip() + "\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
