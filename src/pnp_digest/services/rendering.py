"""Markdown/DOCX/PDF/PPTX brief 렌더링 유틸리티."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from pnp_digest.domain.enums import OutputType
from pnp_digest.domain.models import AudienceExplanation, ExplainArtifact


def default_render_output_path(stage_dir: Path, output_type: OutputType) -> Path:
    """render stage 기본 출력 경로를 반환한다."""

    suffix_by_type = {
        OutputType.MARKDOWN: ".md",
        OutputType.DOCX: ".docx",
        OutputType.PDF: ".pdf",
        OutputType.PPTX: ".pptx",
    }
    return stage_dir / f"brief{suffix_by_type[output_type]}"


def _render_explanation_block(title: str, explanation: AudienceExplanation) -> list[str]:
    """단일 직급 설명 블록을 Markdown 섹션으로 직렬화한다."""

    lines = [
        f"### {title}",
        "",
        f"- purpose: {explanation.purpose}",
        f"- audience_focus: {', '.join(explanation.audience_focus) if explanation.audience_focus else '-'}",
        f"- explanation_text: {explanation.explanation_text}",
        f"- key_points: {', '.join(explanation.key_points) if explanation.key_points else '-'}",
        f"- cautions: {', '.join(explanation.cautions) if explanation.cautions else '-'}",
        f"- action_prompt: {explanation.action_prompt or '-'}",
        "",
    ]
    return lines


def build_markdown_brief(
    explain_artifact: ExplainArtifact,
    *,
    brief_title: str,
) -> str:
    """explain artifact를 사람이 읽는 Markdown brief로 변환한다."""

    lines = [
        f"# {brief_title}",
        "",
        f"- run_id: {explain_artifact.run.run_id}",
        f"- document_count: {len(explain_artifact.explanations)}",
        "",
    ]

    for record in explain_artifact.explanations:
        lines.extend(
            [
                f"## {record.document_title}",
                "",
                f"- document_id: {record.document_id}",
                f"- document_type: {record.document_type}",
                f"- source_review_status: {record.source_review_status}",
                f"- summary_confidence: {record.summary_confidence:.2f}",
                f"- human_review_notes: {record.human_review_notes or '-'}",
                "",
            ]
        )
        lines.extend(_render_explanation_block("신입 설명", record.entry_level_explanation))
        lines.extend(_render_explanation_block("과장 설명", record.manager_level_explanation))
        lines.extend(_render_explanation_block("부장 설명", record.director_level_explanation))

    return "\n".join(lines).rstrip() + "\n"


def _docx_content_types_xml() -> str:
    """DOCX content types XML을 반환한다."""

    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""


def _docx_root_relationships_xml() -> str:
    """DOCX 루트 relationships XML을 반환한다."""

    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""


def _docx_document_relationships_xml() -> str:
    """DOCX document relationships XML을 반환한다."""

    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
"""


def _docx_styles_xml() -> str:
    """최소 paragraph style 정의를 반환한다."""

    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
  </w:style>
</w:styles>
"""


def _docx_core_xml(title: str) -> str:
    """DOCX core properties XML을 반환한다."""

    escaped_title = escape(title)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{escaped_title}</dc:title>
  <dc:creator>PnP Digest</dc:creator>
</cp:coreProperties>
"""


def _docx_app_xml() -> str:
    """DOCX app properties XML을 반환한다."""

    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>PnP Digest</Application>
</Properties>
"""


def _paragraph_xml(text: str, *, style: str | None = None) -> str:
    """단일 문단 XML을 생성한다."""

    escaped_text = escape(text)
    style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return (
        "<w:p>"
        f"{style_xml}"
        f"<w:r><w:t>{escaped_text}</w:t></w:r>"
        "</w:p>"
    )


def _docx_document_xml_from_markdown(markdown_text: str) -> str:
    """Markdown 문자열을 최소 DOCX document XML로 변환한다."""

    paragraphs: list[str] = []
    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if line.startswith("# "):
            paragraphs.append(_paragraph_xml(line[2:], style="Title"))
            continue
        if line.startswith("## "):
            paragraphs.append(_paragraph_xml(line[3:], style="Heading1"))
            continue
        if line.startswith("### "):
            paragraphs.append(_paragraph_xml(line[4:], style="Heading2"))
            continue
        paragraphs.append(_paragraph_xml(line))

    body = "".join(paragraphs)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<w:body>{body}<w:sectPr/></w:body>"
        "</w:document>"
    )


def build_docx_brief(
    explain_artifact: ExplainArtifact,
    *,
    brief_title: str,
) -> bytes:
    """explain artifact를 최소 DOCX bytes로 변환한다."""

    markdown_brief = build_markdown_brief(explain_artifact, brief_title=brief_title)
    document_xml = _docx_document_xml_from_markdown(markdown_brief)

    from io import BytesIO

    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _docx_content_types_xml())
        archive.writestr("_rels/.rels", _docx_root_relationships_xml())
        archive.writestr("docProps/core.xml", _docx_core_xml(brief_title))
        archive.writestr("docProps/app.xml", _docx_app_xml())
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/styles.xml", _docx_styles_xml())
        archive.writestr("word/_rels/document.xml.rels", _docx_document_relationships_xml())
    return buffer.getvalue()


def _pptx_content_types_xml(slide_count: int) -> str:
    """PPTX content types XML을 반환한다."""

    slide_overrides = "\n".join(
        (
            f'  <Override PartName="/ppt/slides/slide{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        )
        for index in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
{slide_overrides}
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""


def _pptx_root_relationships_xml() -> str:
    """PPTX 루트 relationships XML을 반환한다."""

    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""


def _pptx_presentation_xml(slide_count: int) -> str:
    """PPTX presentation XML을 반환한다."""

    slide_ids = "\n".join(
        f'    <p:sldId id="{255 + index}" r:id="rId{index + 1}"/>'
        for index in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" saveSubsetFonts="1" autoCompressPictures="0">
  <p:sldMasterIdLst>
    <p:sldMasterId id="2147483648" r:id="rId1"/>
  </p:sldMasterIdLst>
  <p:sldIdLst>
{slide_ids}
  </p:sldIdLst>
  <p:sldSz cx="9144000" cy="6858000"/>
  <p:notesSz cx="6858000" cy="9144000"/>
  <p:defaultTextStyle/>
</p:presentation>
"""


def _pptx_presentation_rels_xml(slide_count: int) -> str:
    """PPTX presentation relationships XML을 반환한다."""

    slide_rels = "\n".join(
        (
            f'  <Relationship Id="rId{index + 1}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            f'Target="slides/slide{index}.xml"/>'
        )
        for index in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
{slide_rels}
</Relationships>
"""


def _pptx_slide_master_xml() -> str:
    """PPTX slide master XML을 반환한다."""

    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld name="Master Slide">
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst>
    <p:sldLayoutId id="1" r:id="rId1"/>
  </p:sldLayoutIdLst>
  <p:txStyles>
    <p:titleStyle/>
    <p:bodyStyle/>
    <p:otherStyle/>
  </p:txStyles>
</p:sldMaster>
"""


def _pptx_slide_master_rels_xml() -> str:
    """PPTX slide master relationships XML을 반환한다."""

    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>
"""


def _pptx_slide_layout_xml() -> str:
    """PPTX slide layout XML을 반환한다."""

    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
  <p:cSld name="Blank">
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr>
    <a:masterClrMapping/>
  </p:clrMapOvr>
</p:sldLayout>
"""


def _pptx_slide_layout_rels_xml() -> str:
    """PPTX slide layout relationships XML을 반환한다."""

    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>
"""


def _pptx_theme_xml() -> str:
    """PPTX theme XML을 반환한다."""

    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="PnP Digest Theme">
  <a:themeElements>
    <a:clrScheme name="PnP Digest">
      <a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>
      <a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
      <a:dk2><a:srgbClr val="1F1F1F"/></a:dk2>
      <a:lt2><a:srgbClr val="F7F7F7"/></a:lt2>
      <a:accent1><a:srgbClr val="2C5A7A"/></a:accent1>
      <a:accent2><a:srgbClr val="4E8098"/></a:accent2>
      <a:accent3><a:srgbClr val="7BAFD4"/></a:accent3>
      <a:accent4><a:srgbClr val="B0D6F2"/></a:accent4>
      <a:accent5><a:srgbClr val="DCEAF7"/></a:accent5>
      <a:accent6><a:srgbClr val="F4F8FB"/></a:accent6>
      <a:hlink><a:srgbClr val="0000FF"/></a:hlink>
      <a:folHlink><a:srgbClr val="800080"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="PnP Digest Fonts">
      <a:majorFont>
        <a:latin typeface="Calibri"/>
        <a:ea typeface="Malgun Gothic"/>
        <a:cs typeface="Arial"/>
      </a:majorFont>
      <a:minorFont>
        <a:latin typeface="Calibri"/>
        <a:ea typeface="Malgun Gothic"/>
        <a:cs typeface="Arial"/>
      </a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="PnP Digest Format">
      <a:fillStyleLst>
        <a:solidFill><a:schemeClr val="lt1"/></a:solidFill>
      </a:fillStyleLst>
      <a:lineStyleLst>
        <a:ln w="9525"><a:solidFill><a:schemeClr val="dk1"/></a:solidFill></a:ln>
      </a:lineStyleLst>
      <a:effectStyleLst>
        <a:effectStyle><a:effectLst/></a:effectStyle>
      </a:effectStyleLst>
      <a:bgFillStyleLst>
        <a:solidFill><a:schemeClr val="lt1"/></a:solidFill>
      </a:bgFillStyleLst>
    </a:fmtScheme>
  </a:themeElements>
  <a:objectDefaults/>
  <a:extraClrSchemeLst/>
</a:theme>
"""


def _pptx_paragraph_xml(text: str, *, font_size: int = 1800, bold: bool = False) -> str:
    """PPTX 텍스트 문단 XML을 생성한다."""

    bold_xml = ' b="1"' if bold else ""
    return (
        "<a:p>"
        f'<a:r><a:rPr lang="ko-KR" sz="{font_size}"{bold_xml}/><a:t>{escape(text)}</a:t></a:r>'
        '<a:endParaRPr lang="ko-KR"/>'
        "</a:p>"
    )


def _pptx_text_box_xml(
    *,
    shape_id: int,
    shape_name: str,
    x: int,
    y: int,
    cx: int,
    cy: int,
    paragraphs: list[str],
    font_size: int,
    bold_first: bool = False,
) -> str:
    """단일 텍스트 박스 shape XML을 생성한다."""

    paragraph_xml = "".join(
        _pptx_paragraph_xml(
            paragraph,
            font_size=font_size,
            bold=bold_first and index == 0,
        )
        for index, paragraph in enumerate(paragraphs)
    ) or _pptx_paragraph_xml("", font_size=font_size)
    return f"""<p:sp>
  <p:nvSpPr>
    <p:cNvPr id="{shape_id}" name="{escape(shape_name)}"/>
    <p:cNvSpPr txBox="1"/>
    <p:nvPr/>
  </p:nvSpPr>
  <p:spPr>
    <a:xfrm>
      <a:off x="{x}" y="{y}"/>
      <a:ext cx="{cx}" cy="{cy}"/>
    </a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:noFill/>
    <a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square"/>
    <a:lstStyle/>
    {paragraph_xml}
  </p:txBody>
</p:sp>
"""


def _pptx_slide_xml(
    explain_artifact: ExplainArtifact,
    slide_index: int,
    *,
    brief_title: str,
) -> str:
    """단일 PPTX slide XML을 생성한다."""

    if explain_artifact.explanations:
        record = explain_artifact.explanations[slide_index]
        body_lines = [
            record.document_title,
            f"document_id: {record.document_id}",
            f"document_type: {record.document_type}",
            f"source_review_status: {record.source_review_status}",
            f"summary_confidence: {record.summary_confidence:.2f}",
            f"human_review_notes: {record.human_review_notes or '-'}",
            "",
            "[신입 설명]",
            record.entry_level_explanation.explanation_text,
            "key_points: " + (", ".join(record.entry_level_explanation.key_points) or "-"),
            "",
            "[과장 설명]",
            record.manager_level_explanation.explanation_text,
            "key_points: " + (", ".join(record.manager_level_explanation.key_points) or "-"),
            "",
            "[부장 설명]",
            record.director_level_explanation.explanation_text,
            "key_points: " + (", ".join(record.director_level_explanation.key_points) or "-"),
        ]
    else:
        body_lines = [
            "No explanations were included in this deck.",
            f"run_id: {explain_artifact.run.run_id}",
        ]

    title_box = _pptx_text_box_xml(
        shape_id=2,
        shape_name="Title 1",
        x=457200,
        y=274320,
        cx=8229600,
        cy=685800,
        paragraphs=[brief_title],
        font_size=2400,
        bold_first=True,
    )
    body_box = _pptx_text_box_xml(
        shape_id=3,
        shape_name="Content 1",
        x=457200,
        y=1143000,
        cx=8229600,
        cy=4800600,
        paragraphs=body_lines,
        font_size=1400,
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld name="Slide {slide_index + 1}">
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
      {title_box}
      {body_box}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr>
    <a:masterClrMapping/>
  </p:clrMapOvr>
</p:sld>
"""


def _pptx_slide_rels_xml() -> str:
    """단일 slide relationships XML을 반환한다."""

    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>
"""


def build_pptx_brief(
    explain_artifact: ExplainArtifact,
    *,
    brief_title: str,
) -> bytes:
    """explain artifact를 최소 PPTX bytes로 변환한다."""

    from io import BytesIO

    slide_count = max(len(explain_artifact.explanations), 1)
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _pptx_content_types_xml(slide_count))
        archive.writestr("_rels/.rels", _pptx_root_relationships_xml())
        archive.writestr("docProps/core.xml", _docx_core_xml(brief_title))
        archive.writestr("docProps/app.xml", _docx_app_xml())
        archive.writestr("ppt/presentation.xml", _pptx_presentation_xml(slide_count))
        archive.writestr("ppt/_rels/presentation.xml.rels", _pptx_presentation_rels_xml(slide_count))
        archive.writestr("ppt/slideMasters/slideMaster1.xml", _pptx_slide_master_xml())
        archive.writestr(
            "ppt/slideMasters/_rels/slideMaster1.xml.rels",
            _pptx_slide_master_rels_xml(),
        )
        archive.writestr("ppt/slideLayouts/slideLayout1.xml", _pptx_slide_layout_xml())
        archive.writestr(
            "ppt/slideLayouts/_rels/slideLayout1.xml.rels",
            _pptx_slide_layout_rels_xml(),
        )
        archive.writestr("ppt/theme/theme1.xml", _pptx_theme_xml())
        for slide_index in range(slide_count):
            archive.writestr(
                f"ppt/slides/slide{slide_index + 1}.xml",
                _pptx_slide_xml(
                    explain_artifact,
                    slide_index,
                    brief_title=brief_title,
                ),
            )
            archive.writestr(
                f"ppt/slides/_rels/slide{slide_index + 1}.xml.rels",
                _pptx_slide_rels_xml(),
            )
    return buffer.getvalue()


def _pdf_escape_hex_text(text: str) -> str:
    """PDF hex string에 넣기 위한 UTF-16BE 문자열을 생성한다."""

    return text.encode("utf-16-be").hex().upper()


def _pdf_line_layout(markdown_text: str) -> list[list[tuple[int, str]]]:
    """Markdown 텍스트를 PDF 페이지/행 배치 단위로 나눈다."""

    top_margin = 792
    bottom_margin = 48
    current_y = top_margin
    current_page: list[tuple[int, str]] = []
    pages: list[list[tuple[int, str]]] = []

    def flush_page() -> None:
        nonlocal current_page
        if current_page:
            pages.append(current_page)
            current_page = []

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        if not line:
            current_y -= 10
            if current_y < bottom_margin:
                flush_page()
                current_y = top_margin
            continue

        if line.startswith("# "):
            font_size = 18
            text = line[2:]
        elif line.startswith("## "):
            font_size = 16
            text = line[3:]
        elif line.startswith("### "):
            font_size = 14
            text = line[4:]
        else:
            font_size = 11
            text = line

        required_height = font_size + 6
        if current_y - required_height < bottom_margin:
            flush_page()
            current_y = top_margin

        current_page.append((font_size, text))
        current_y -= required_height

    flush_page()
    return pages or [[]]


def _pdf_font_objects() -> tuple[bytes, bytes]:
    """한글을 포함한 최소 Type0 font 객체 정의를 반환한다."""

    type0_font = (
        "<< /Type /Font /Subtype /Type0 /BaseFont /HYGoThic-Medium "
        "/Encoding /UniKS-UCS2-H /DescendantFonts [4 0 R] >>"
    ).encode("ascii")
    descendant_font = (
        "<< /Type /Font /Subtype /CIDFontType0 /BaseFont /HYGoThic-Medium "
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (Korea1) /Supplement 1 >> "
        "/DW 1000 >>"
    ).encode("ascii")
    return type0_font, descendant_font


def _pdf_page_stream(page_lines: list[tuple[int, str]]) -> bytes:
    """단일 PDF 페이지용 content stream을 생성한다."""

    commands = ["BT"]
    current_y = 792
    for font_size, text in page_lines:
        commands.append(f"/F1 {font_size} Tf")
        commands.append(f"1 0 0 1 48 {current_y} Tm")
        commands.append(f"<{_pdf_escape_hex_text(text)}> Tj")
        current_y -= font_size + 6
    commands.append("ET")
    return "\n".join(commands).encode("ascii")


def build_pdf_brief(
    explain_artifact: ExplainArtifact,
    *,
    brief_title: str,
) -> bytes:
    """explain artifact를 최소 PDF bytes로 변환한다."""

    markdown_brief = build_markdown_brief(explain_artifact, brief_title=brief_title)
    page_layouts = _pdf_line_layout(markdown_brief)
    type0_font, descendant_font = _pdf_font_objects()

    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: type0_font,
        4: descendant_font,
    }

    next_object_id = 5
    page_ids: list[int] = []
    for page_lines in page_layouts:
        stream = _pdf_page_stream(page_lines)
        content_id = next_object_id
        page_id = next_object_id + 1
        next_object_id += 2

        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii")
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[2] = (
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>"
    ).encode("ascii")

    max_object_id = max(objects)
    pdf_bytes = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"
    offsets = [0] * (max_object_id + 1)

    for object_id in range(1, max_object_id + 1):
        body = objects[object_id]
        offsets[object_id] = len(pdf_bytes)
        pdf_bytes += f"{object_id} 0 obj\n".encode("ascii")
        pdf_bytes += body + b"\nendobj\n"

    xref_offset = len(pdf_bytes)
    pdf_bytes += f"xref\n0 {max_object_id + 1}\n".encode("ascii")
    pdf_bytes += b"0000000000 65535 f \n"
    for object_id in range(1, max_object_id + 1):
        pdf_bytes += f"{offsets[object_id]:010d} 00000 n \n".encode("ascii")
    pdf_bytes += (
        f"trailer\n<< /Size {max_object_id + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("ascii")
    return pdf_bytes
