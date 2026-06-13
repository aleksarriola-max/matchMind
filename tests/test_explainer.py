from backend.engines import explainer


def test_route_offside():
    assert explainer.route("Why was the goal disallowed for offside in the 27th minute?") == "offside_27"


def test_route_handball():
    assert explainer.route("Why didn't the referee award a penalty for the handball appeal?") == "handball_38"


def test_route_halftime_shift():
    assert explainer.route("Why did the team switch from a 4-3-3 to a 4-4-2 formation at halftime?") == "halftime_shift"


def test_route_substitution():
    assert explainer.route("Why did they make a substitution and bring on a fresh winger in the 58th minute?") == "sub_58"


def test_route_goal_home_1():
    assert explainer.route("How did the equaliser happen to make it 1-1?") == "goal_home_1"


def test_route_fatigue():
    assert explainer.route("Why did Borealia's pressing collapse due to fatigue late on?") == "fatigue_71"


def test_route_goal_home_2():
    assert explainer.route("How was the winning goal scored from the corner?") == "goal_home_2"


def test_route_general_question_returns_none():
    assert explainer.route("What's the weather forecast for the stadium tonight?") is None


def test_route_tie_breaks_to_lowest_minute():
    assert explainer.route("Tell me about the offside call and the corner routine") == "offside_27"
