"""Chat workflow (supervisor) for orchestrating the agent."""

import json
import logging
import re
from typing import Any, Dict, List, Literal

from langgraph.graph import END, StateGraph
from langsmith import traceable

from udemy_agent.data import UDEMY_KNOWLEDGE
from udemy_agent.models import BrowserFilters, UdemyBrowserState, UdemyChatState
from udemy_agent.prompts import (
    CLASSIFY_SYSTEM_PROMPT,
    CLASSIFY_USER_PROMPT,
    COMPARISON_SYSTEM_PROMPT,
    COMPARISON_USER_PROMPT,
    COMPLEX_QUERY_SYSTEM_PROMPT,
    COMPLEX_QUERY_USER_PROMPT,
    COURSE_DETAIL_SYNTHESIZE_PROMPT,
    COURSE_DETAIL_SYNTHESIZE_USER,
    DIRECT_RESPONSE_SYSTEM_PROMPT,
    SYNTHESIZE_SYSTEM_PROMPT,
    SYNTHESIZE_USER_PROMPT,
)
from udemy_agent.services import get_llm_service
from udemy_agent.core.workflows.browser import build_browser_workflow
from udemy_agent.core.workflows.detail import build_course_detail_workflow

logger = logging.getLogger("udemy_agent.workflow.chat")

# Compiled graph cache
_browser_graph = None
_course_detail_graph = None


def get_browser_graph():
    """Get cached compiled browser workflow."""
    global _browser_graph
    if _browser_graph is None:
        _browser_graph = build_browser_workflow().compile()
    return _browser_graph


def get_course_detail_graph():
    """Get cached compiled course detail workflow."""
    global _course_detail_graph
    if _course_detail_graph is None:
        _course_detail_graph = build_course_detail_workflow().compile()
    return _course_detail_graph


@traceable(name="classify_intent", run_type="chain")
async def classify_node(state: UdemyChatState) -> dict:
    """Classify the user's intent and extract filters."""
    logger.info("Classifying user intent...")

    llm = get_llm_service()

    user_message = ""
    for msg in reversed(state.messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break

    if not user_message:
        return {"user_intent": "chat", "needs_browser": False, "status": "responding"}

    try:
        has_previous_results = state.last_search_results is not None and len(state.last_search_results or []) > 0
        previous_results_summary = ""

        if has_previous_results:
            courses = state.last_search_results[:10]
            summary_lines = ["Previously shown courses:"]
            for i, course in enumerate(courses, 1):
                title = course.get("title", "Unknown")[:60]
                summary_lines.append(f"  {i}. {title}")
            previous_results_summary = "\n".join(summary_lines)

        user_prompt = CLASSIFY_USER_PROMPT.format(
            message=user_message,
            has_previous_results=has_previous_results,
            previous_results_summary=previous_results_summary if has_previous_results else "No previous results."
        )

        response = await llm.call(CLASSIFY_SYSTEM_PROMPT, user_prompt)
        classification = _parse_classification(response)
        logger.info(f"Intent: {classification.get('intent')}, Query: {classification.get('search_query')}")

        # Extract filters
        filters_dict = classification.get("filters", {})
        browser_filters = BrowserFilters(
            sort_by=filters_dict.get("sort_by"),
            min_rating=filters_dict.get("min_rating"),
            duration=filters_dict.get("duration"),
            level=filters_dict.get("level"),
            price=filters_dict.get("price"),
            max_results=filters_dict.get("max_results", 20),
        ) if filters_dict else BrowserFilters()

        # Handle course_details intent
        intent = classification.get("intent", "chat")
        target_course_url = classification.get("course_url")
        target_course_index = None

        if intent == "course_details":
            course_index = classification.get("course_index")
            if course_index and state.last_search_results:
                try:
                    idx = int(course_index) - 1
                    if 0 <= idx < len(state.last_search_results):
                        course = state.last_search_results[idx]
                        target_course_url = course.get("url")
                        target_course_index = int(course_index)
                except (ValueError, IndexError):
                    pass

            if not target_course_url:
                return {
                    "user_intent": "chat",
                    "needs_browser": False,
                    "response": "Please search for courses first, then ask about a specific one.",
                    "status": "done",
                }

        # Handle compare_courses intent
        compare_course_indices = None
        compare_course_urls = None

        if intent == "compare_courses":
            compare_indices = classification.get("compare_indices", [])
            if compare_indices and state.last_search_results:
                compare_course_indices = []
                compare_course_urls = []
                for idx in compare_indices:
                    try:
                        i = int(idx) - 1
                        if 0 <= i < len(state.last_search_results):
                            course = state.last_search_results[i]
                            compare_course_indices.append(int(idx))
                            if course.get("url"):
                                compare_course_urls.append(course.get("url"))
                    except (ValueError, IndexError):
                        pass

                if len(compare_course_urls) < 2:
                    return {
                        "user_intent": "chat",
                        "needs_browser": False,
                        "response": "I need at least 2 courses to compare. Search first, then ask to compare.",
                        "status": "done",
                    }
            else:
                return {
                    "user_intent": "chat",
                    "needs_browser": False,
                    "response": "Please search for courses first, then I can compare them.",
                    "status": "done",
                }

        # Handle complex_query intent
        complex_query_plan = None
        if intent == "complex_query":
            complex_steps = classification.get("complex_steps", [])
            if complex_steps:
                complex_query_plan = [{"step": i+1, "action": step} for i, step in enumerate(complex_steps)]

        return {
            "user_intent": intent,
            "needs_browser": classification.get("needs_browser", False),
            "browser_task": classification.get("browser_task"),
            "search_query": classification.get("search_query"),
            "browser_filters": browser_filters,
            "target_course_url": target_course_url,
            "target_course_index": target_course_index,
            "compare_course_indices": compare_course_indices,
            "compare_course_urls": compare_course_urls,
            "complex_query_plan": complex_query_plan,
            "capture_screenshots": classification.get("capture_screenshots", False),
            "status": "browsing" if classification.get("needs_browser") else "responding",
        }

    except Exception as e:
        logger.error(f"Classification error: {e}", exc_info=True)
        return {"user_intent": "chat", "needs_browser": False, "status": "responding"}


def _parse_classification(response_text: str) -> Dict:
    """Parse classification from LLM response."""
    try:
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        elif "{" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            json_str = response_text[start:end]
        else:
            return {"intent": "chat", "needs_browser": False}

        classification = json.loads(json_str)
        valid_intents = ["trending", "top_rated", "new_courses", "search", "category",
                        "course_details", "compare_courses", "complex_query", "chat"]

        if classification.get("intent") not in valid_intents:
            classification["intent"] = "chat"

        if classification.get("filters"):
            for key in ["sort_by", "min_rating", "duration", "level", "price"]:
                if classification["filters"].get(key) in [None, "null", ""]:
                    classification["filters"][key] = None

        return classification
    except (json.JSONDecodeError, ValueError):
        return {"intent": "chat", "needs_browser": False}


@traceable(name="invoke_browser_agent", run_type="chain")
async def invoke_browser_node(state: UdemyChatState) -> dict:
    """Invoke the Browser Agent to fetch Udemy courses."""
    logger.info(f"Browser task: {state.browser_task}, Intent: {state.user_intent}")

    if state.user_intent == "course_details":
        return await _handle_course_details(state)

    if state.user_intent == "compare_courses":
        return await _handle_course_comparison(state)

    if state.user_intent == "complex_query":
        return await _handle_complex_query(state)

    if not state.browser_task:
        return {"browser_result": {"error": "No browser task specified"}, "status": "synthesizing"}

    try:
        browser_state = UdemyBrowserState(
            objective=state.browser_task,
            task_type=state.user_intent or "trending",
            search_query=state.search_query,
            filters=state.browser_filters,
        )

        browser_graph = get_browser_graph()
        final_state = None

        async for event in browser_graph.astream(browser_state):
            if isinstance(event, dict):
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        if final_state is None:
                            final_state = node_output
                        else:
                            final_state.update(node_output)

        courses = final_state.get("extracted_courses", []) if final_state else []
        result = {
            "status": final_state.get("status", "unknown") if final_state else "error",
            "courses": courses,
            "current_url": final_state.get("current_url", "") if final_state else "",
        }
        page_content = final_state.get("page_text", "") if final_state else ""

        return {
            "browser_result": result,
            "browser_page_content": page_content[:30000] if page_content else None,
            "last_search_results": courses,
            "status": "synthesizing",
        }

    except Exception as e:
        logger.error(f"Browser invocation error: {e}", exc_info=True)
        return {"browser_result": {"error": str(e), "status": "error", "courses": []}, "status": "synthesizing"}


async def _handle_course_details(state: UdemyChatState) -> dict:
    """Handle course details request."""
    course_url = state.target_course_url
    if not course_url:
        return {"browser_result": {"error": "No course URL available"}, "status": "synthesizing"}

    try:
        browser_state = UdemyBrowserState(
            objective="Get course details",
            task_type="course_details",
            course_detail_url=course_url,
        )

        detail_graph = get_course_detail_graph()
        final_state = None

        async for event in detail_graph.astream(browser_state):
            if isinstance(event, dict):
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        if final_state is None:
                            final_state = node_output
                        else:
                            final_state.update(node_output)

        course_details = final_state.get("course_details") if final_state else None
        page_content = final_state.get("page_text", "") if final_state else ""

        if course_details:
            result = {"status": "done", "course_details": course_details, "current_url": course_url}
        else:
            result = {"status": "error", "error": "Failed to extract course details"}

        return {
            "browser_result": result,
            "browser_page_content": page_content[:30000] if page_content else None,
            "status": "synthesizing",
        }

    except Exception as e:
        logger.error(f"Course details error: {e}", exc_info=True)
        return {"browser_result": {"error": str(e), "status": "error"}, "status": "synthesizing"}


async def _handle_course_comparison(state: UdemyChatState) -> dict:
    """Handle course comparison request."""
    course_urls = state.compare_course_urls
    course_indices = state.compare_course_indices

    if not course_urls or len(course_urls) < 2:
        return {"browser_result": {"error": "Need at least 2 courses to compare"}, "status": "synthesizing"}

    comparison_data = []

    for i, url in enumerate(course_urls[:3]):
        course_idx = course_indices[i] if course_indices and i < len(course_indices) else i + 1

        try:
            browser_state = UdemyBrowserState(
                objective=f"Get details for course {course_idx}",
                task_type="course_details",
                course_detail_url=url,
            )

            detail_graph = get_course_detail_graph()
            final_state = None

            async for event in detail_graph.astream(browser_state):
                if isinstance(event, dict):
                    for node_name, node_output in event.items():
                        if isinstance(node_output, dict):
                            if final_state is None:
                                final_state = node_output
                            else:
                                final_state.update(node_output)

            course_details = final_state.get("course_details") if final_state else None
            if course_details:
                course_details["course_index"] = course_idx
                course_details["url"] = url
                comparison_data.append(course_details)

        except Exception as e:
            comparison_data.append({"course_index": course_idx, "url": url, "error": str(e)})

    return {
        "browser_result": {"status": "done", "comparison_data": comparison_data},
        "comparison_result": {"courses": comparison_data, "comparison_type": "detailed"},
        "status": "synthesizing",
    }


async def _handle_complex_query(state: UdemyChatState) -> dict:
    """Handle complex multi-step queries."""
    plan = state.complex_query_plan
    if not plan:
        return {"browser_result": {"error": "No execution plan for complex query"}, "status": "synthesizing"}

    results = []
    search_query = state.search_query
    filters = state.browser_filters

    try:
        browser_state = UdemyBrowserState(
            objective=f"Search for {search_query} courses",
            task_type="search",
            search_query=search_query,
            filters=filters,
        )

        browser_graph = get_browser_graph()
        final_state = None

        async for event in browser_graph.astream(browser_state):
            if isinstance(event, dict):
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        if final_state is None:
                            final_state = node_output
                        else:
                            final_state.update(node_output)

        courses = final_state.get("extracted_courses", []) if final_state else []
        results.append({"step": 1, "action": "search", "courses_found": len(courses)})

        if not courses:
            return {
                "browser_result": {"status": "done", "courses": [], "complex_results": results},
                "status": "synthesizing",
            }

        # Apply sorting based on query
        user_message = ""
        for msg in reversed(state.messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "").lower()
                break

        filtered_courses = courses.copy()

        if any(word in user_message for word in ["cheap", "cheapest", "affordable", "budget"]):
            def get_price_value(course):
                price = course.get("price", "$999")
                if price.lower() == "free":
                    return 0
                try:
                    return float(re.sub(r'[^\d.]', '', price))
                except:
                    return 999
            filtered_courses.sort(key=get_price_value)
            results.append({"step": 2, "action": "sort_by_price"})

        elif any(word in user_message for word in ["best", "top", "highly rated"]):
            def get_rating_value(course):
                try:
                    return float(course.get("rating", "0"))
                except:
                    return 0
            filtered_courses.sort(key=get_rating_value, reverse=True)
            results.append({"step": 2, "action": "sort_by_rating"})

        return {
            "browser_result": {"status": "done", "courses": filtered_courses, "complex_results": results},
            "complex_query_results": results,
            "last_search_results": filtered_courses,
            "status": "synthesizing",
        }

    except Exception as e:
        logger.error(f"Complex query error: {e}", exc_info=True)
        return {"browser_result": {"error": str(e), "status": "error"}, "status": "synthesizing"}


@traceable(name="synthesize_response", run_type="chain")
async def synthesize_node(state: UdemyChatState) -> dict:
    """Synthesize browser results into a conversational response."""
    logger.info(f"Synthesizing results for intent: {state.user_intent}")

    llm = get_llm_service()
    browser_result = state.browser_result or {}

    if browser_result.get("error"):
        return {"response": f"I encountered an issue: {browser_result['error']}", "status": "done"}

    if state.user_intent == "course_details":
        return await _synthesize_course_details(state, browser_result, llm)

    if state.user_intent == "compare_courses":
        return await _synthesize_comparison(state, browser_result, llm)

    if state.user_intent == "complex_query":
        return await _synthesize_complex_query(state, browser_result, llm)

    courses = browser_result.get("courses", [])
    if not courses:
        return {"response": "I couldn't find any courses matching your request.", "status": "done"}

    user_message = ""
    for msg in reversed(state.messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break

    filters_str = state.browser_filters.describe() if state.browser_filters else "None"
    courses_json = json.dumps(courses[:15], indent=2)

    additional_context = ""
    if state.browser_page_content:
        additional_context = f"Additional Page Context:\n{state.browser_page_content[:3000]}"

    try:
        user_prompt = SYNTHESIZE_USER_PROMPT.format(
            user_message=user_message,
            task_type=state.user_intent or "general",
            search_query=state.search_query or "N/A",
            filters_applied=filters_str,
            source_url=browser_result.get("current_url", "N/A"),
            course_count=len(courses),
            courses_json=courses_json,
            additional_context=additional_context,
        )

        response = await llm.call(SYNTHESIZE_SYSTEM_PROMPT, user_prompt)

        if len(courses) > 15:
            response += f"\n\n*Showing details for top 15 of {len(courses)} courses found.*"

        return {"response": response, "status": "done"}

    except Exception as e:
        return {"response": f"I found {len(courses)} courses but had trouble generating a response.", "status": "done"}


async def _synthesize_course_details(state: UdemyChatState, browser_result: Dict, llm) -> dict:
    """Synthesize course detail results."""
    course_details = browser_result.get("course_details")
    if not course_details:
        return {"response": "I couldn't retrieve the course details.", "status": "done"}

    user_message = ""
    for msg in reversed(state.messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break

    page_context = state.browser_page_content[:3000] if state.browser_page_content else "N/A"

    try:
        user_prompt = COURSE_DETAIL_SYNTHESIZE_USER.format(
            user_message=user_message,
            course_details_json=json.dumps(course_details, indent=2),
            page_context=page_context,
        )

        response = await llm.call(COURSE_DETAIL_SYNTHESIZE_PROMPT, user_prompt)

        course_url = course_details.get("url") or browser_result.get("current_url")
        if course_url:
            response += f"\n\n**Course Link:** {course_url}"

        return {"response": response, "status": "done"}

    except Exception as e:
        title = course_details.get("title", "Unknown Course")
        return {"response": f"**{title}**\nError formatting details: {e}", "status": "done"}


async def _synthesize_comparison(state: UdemyChatState, browser_result: Dict, llm) -> dict:
    """Synthesize course comparison results."""
    comparison_data = browser_result.get("comparison_data", [])
    if not comparison_data or len(comparison_data) < 2:
        return {"response": "I couldn't gather enough information to compare these courses.", "status": "done"}

    user_message = ""
    for msg in reversed(state.messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break

    try:
        user_prompt = COMPARISON_USER_PROMPT.format(
            user_message=user_message,
            courses_json=json.dumps(comparison_data, indent=2),
        )

        response = await llm.call(COMPARISON_SYSTEM_PROMPT, user_prompt)

        links = []
        for course in comparison_data:
            idx = course.get("course_index", "")
            title = course.get("title", "Unknown")[:50]
            url = course.get("url", "")
            if url:
                links.append(f"- Course {idx}: {title}\n  {url}")

        if links:
            response += "\n\n**Course Links:**\n" + "\n".join(links)

        return {"response": response, "status": "done"}

    except Exception as e:
        return {"response": "Error generating comparison.", "status": "done"}


async def _synthesize_complex_query(state: UdemyChatState, browser_result: Dict, llm) -> dict:
    """Synthesize complex query results."""
    courses = browser_result.get("courses", [])
    complex_results = browser_result.get("complex_results", [])

    if not courses:
        return {"response": "I couldn't find courses matching your criteria.", "status": "done"}

    user_message = ""
    for msg in reversed(state.messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break

    steps_text = "\n".join([f"- Step {r['step']}: {r['action']}" for r in complex_results])

    try:
        user_prompt = COMPLEX_QUERY_USER_PROMPT.format(
            user_message=user_message,
            analysis_steps=steps_text,
            courses_json=json.dumps(courses[:10], indent=2),
            detailed_info="",
        )

        response = await llm.call(COMPLEX_QUERY_SYSTEM_PROMPT, user_prompt)
        return {"response": response, "last_search_results": courses, "status": "done"}

    except Exception as e:
        return {"response": f"Found {len(courses)} courses but had trouble generating response.", "status": "done"}


@traceable(name="direct_response", run_type="chain")
async def respond_node(state: UdemyChatState) -> dict:
    """Direct response node for non-browser requests."""
    llm = get_llm_service()

    user_message = ""
    for msg in reversed(state.messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break

    popular_topics = list(UDEMY_KNOWLEDGE.popular_topics.keys())[:20]
    topics_str = ", ".join(popular_topics)
    system_prompt = DIRECT_RESPONSE_SYSTEM_PROMPT.format(topics_str=topics_str)

    response = await llm.call(system_prompt, user_message)
    return {"response": response, "status": "done"}


def route_after_classify(state: UdemyChatState) -> Literal["invoke_browser", "respond"]:
    """Route after classification."""
    if state.needs_browser:
        return "invoke_browser"
    return "respond"


def build_chat_workflow() -> StateGraph:
    """Build the Chat Agent (Supervisor) workflow."""
    workflow = StateGraph(UdemyChatState)
    workflow.add_node("classify", classify_node)
    workflow.add_node("invoke_browser", invoke_browser_node)
    workflow.add_node("synthesize", synthesize_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("classify")
    workflow.add_conditional_edges(
        "classify",
        route_after_classify,
        {"invoke_browser": "invoke_browser", "respond": "respond"},
    )
    workflow.add_edge("invoke_browser", "synthesize")
    workflow.add_edge("synthesize", END)
    workflow.add_edge("respond", END)

    return workflow
