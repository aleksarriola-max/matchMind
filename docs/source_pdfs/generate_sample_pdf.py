"""One-time script to generate the sample Laws of the Game excerpt PDF
used to demonstrate the Docling ingestion pipeline. Not part of the
runtime app -- run once, the output PDF is committed, this script can
be deleted afterward.
"""
from pathlib import Path

from fpdf import FPDF

OUTPUT_PATH = Path(__file__).resolve().parent / "laws_of_the_game_excerpt.pdf"

LAW_11 = [
    "A player is in an offside position if any part of the head, body, or "
    "feet is in the opponents' half of the field of play, excluding the "
    "halfway line, and any part of the head, body, or feet is nearer to "
    "the opponents' goal line than both the ball and the second-last "
    "opponent. The hands and arms of every player, including the "
    "goalkeepers, are not considered for this purpose.",
    "A player is not in an offside position if level with the second-last "
    "opponent, or level with the last two opponents.",
    "It is not an offence in itself to be in an offside position. A "
    "player in an offside position at the moment the ball is played or "
    "touched by a teammate is only penalised on becoming involved in "
    "active play by interfering with play, interfering with an opponent, "
    "or gaining an advantage by being in that position.",
]

LAW_12 = [
    "A direct free kick is awarded to the opposing team if a player "
    "handles the ball deliberately, except for a goalkeeper within their "
    "own penalty area.",
    "It is a handball offence if a player deliberately touches the ball "
    "with their hand or arm, including moving the hand or arm towards "
    "the ball, or scores in the opponents' goal directly from their hand "
    "or arm, even if accidental.",
    "It is usually an offence if a player touches the ball with their "
    "hand or arm when it has made their body unnaturally bigger, or "
    "touches the ball with their hand or arm when it is above the "
    "height of their shoulder, unless the player has deliberately played "
    "the ball and it then touches their own hand or arm.",
    "It is not usually an offence if the ball touches a player's hand or "
    "arm directly from the player's own head or body, the head or body "
    "of another player who is close, or the player's own hand or arm "
    "when it is close to their body and does not make their body "
    "unnaturally bigger.",
]


def build_pdf() -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Laws of the Game -- Excerpt (Sample)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Law 11 -- Offside", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for paragraph in LAW_11:
        pdf.multi_cell(0, 6, paragraph)
        pdf.ln(2)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Law 12 -- Fouls and Misconduct: Handball", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for paragraph in LAW_12:
        pdf.multi_cell(0, 6, paragraph)
        pdf.ln(2)

    pdf.output(str(OUTPUT_PATH))
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
