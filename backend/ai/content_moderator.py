"""
Content Moderation System for AI-Generated Games
Validates educational value, age-appropriateness, and content safety.

FEATURES:
- Validate educational alignment
- Check age-appropriate language
- Detect inappropriate content
- Ensure learning value
- Cultural sensitivity check
- GENERIC: Works with any game
- ADDITIVE: Doesn't modify existing games unless requested
"""

import json
import re
from typing import Dict, Any, List, Tuple, Optional, Set
from datetime import datetime
import os
from pathlib import Path
import sys

# Add parent directory to imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Optional: OpenAI for advanced content analysis
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class ContentModerator:
    """Moderates AI-generated game content for safety and educational value."""
    
    def __init__(self, use_ai_moderation: bool = True):
        """
        Initialize content moderator.
        
        Args:
            use_ai_moderation: Use AI for advanced content analysis (requires OpenAI API)
        """
        self.use_ai_moderation = use_ai_moderation and OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY")
        
        if self.use_ai_moderation:
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Load content dictionaries
        self._load_content_dictionaries()
        
        # Moderation results
        self.violations = []
        self.warnings = []
        self.educational_value_score = 0
    
    def _load_content_dictionaries(self):
        """Load dictionaries for content filtering."""
        # Inappropriate content patterns
        self.inappropriate_patterns = [
            # Violence
            r'\b(kill|murder|death|violence|blood|gore|weapon)\b',
            # Adult content
            r'\b(sexual|sex|adult|explicit|nude|nsfw)\b',
            # Drugs/alcohol
            r'\b(drug|drugs|alcohol|drunk|cocaine|marijuana|weed)\b',
            # Profanity (mild - just flagging, not blocking)
            r'\b(damn|hell|crap|stupid|idiot)\b',
            # Gambling
            r'\b(gambling|casino|bet|betting)\b'
        ]
        
        # Age-inappropriate language patterns
        self.age_inappropriate = {
            "6-9": [  # Elementary
                r'\b(complex|analyze|synthesis|paradigm|algorithm)\b',
                r'\b(sophisticated|advanced|intricate)\b'
            ],
            "10-12": [  # Middle school
                r'\b(existential|philosophical|metaphysical)\b',
                r'\b(paradigm shift|quantum|relativity)\b'
            ],
            "13-17": [],  # Teens - most content OK
            "18+": []  # Adults - all content OK
        }
        
        # Positive educational indicators
        self.educational_indicators = [
            'learn', 'understand', 'knowledge', 'skill', 'practice',
            'discover', 'explore', 'analyze', 'think', 'solve',
            'create', 'build', 'design', 'plan', 'strategy',
            'decision', 'consequence', 'cause', 'effect', 'result',
            'improve', 'grow', 'develop', 'master', 'achieve'
        ]
        
        # Cultural sensitivity patterns
        self.culturally_sensitive_terms = [
            # Stereotypes
            r'\b(stereotype|racial|racism|sexist|gender bias)\b',
            # Religious
            r'\b(religious conflict|holy war|crusade|jihad)\b',
            # Political
            r'\b(political propaganda|partisan|extremist)\b'
        ]
    
    def moderate_text(self, text: str) -> Dict[str, Any]:
        """Moderate a single free-text capture (e.g. a field-mission note).

        Lightweight, regex-driven scoring suitable for student-submitted text.
        Uses the same ``inappropriate_patterns`` and ``culturally_sensitive_terms``
        already loaded for game moderation, plus a small bag of red-flag keywords
        commonly seen in toxic input.

        Returns a dict::

            {
                "flagged": bool,           # True if score >= 0.85
                "score":   float,          # 0.0–1.0, higher = more concerning
                "categories": list[str],   # which buckets matched
            }
        """
        if not isinstance(text, str) or not text.strip():
            return {"flagged": False, "score": 0.0, "categories": []}

        lowered = text.lower()
        categories: List[str] = []
        score = 0.0

        # Bucket 1: inappropriate patterns (violence/sex/drugs etc.)
        for pattern in self.inappropriate_patterns:
            if re.search(pattern, lowered, re.IGNORECASE):
                # Heavy buckets weigh more than mild ones
                if any(w in pattern for w in ["kill", "murder", "sexual", "drug", "cocaine"]):
                    score += 0.45
                    if "toxicity" not in categories:
                        categories.append("toxicity")
                else:
                    score += 0.15
                    if "mild_profanity" not in categories:
                        categories.append("mild_profanity")

        # Bucket 2: cultural sensitivity / bias
        for pattern in self.culturally_sensitive_terms:
            if re.search(pattern, lowered, re.IGNORECASE):
                score += 0.20
                if "bias" not in categories:
                    categories.append("bias")

        # Bucket 3: explicit red-flag keywords (hate speech, threats, self-harm)
        red_flags = {
            "hate":      [r"\bhate\s+\w+", r"\bracist\b", r"\bbigot\w*\b"],
            "threat":    [r"\bi\s+will\s+(hurt|kill|harm)\b", r"\bthreaten\b"],
            "self_harm": [r"\bsuicid\w*\b", r"\bself[-\s]?harm\b", r"\bcut\s+myself\b"],
        }
        for cat, patterns in red_flags.items():
            for p in patterns:
                if re.search(p, lowered, re.IGNORECASE):
                    score += 0.50
                    if cat not in categories:
                        categories.append(cat)
                    break  # one hit per bucket is enough

        score = min(1.0, round(score, 4))
        return {
            "flagged": score >= 0.85,
            "score": score,
            "categories": categories,
        }

    def moderate_game(
        self,
        game_config: Dict[str, Any],
        target_audience: Optional[str] = None,
        strict_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Moderate complete game configuration.
        
        Args:
            game_config: Game JSON to moderate
            target_audience: Target age range (e.g., "10-12", "13-17")
            strict_mode: If True, apply stricter rules
        
        Returns:
            Moderation report with violations, warnings, and scores
        """
        print(f"🔍 Moderating game: {game_config.get('title', 'Untitled')}")
        
        # Clear previous results
        self.violations = []
        self.warnings = []
        self.educational_value_score = 0
        
        # Extract target audience
        if not target_audience:
            target_audience = game_config.get("target_audience", "13-17")
        
        # 1. Check basic structure
        self._check_structure(game_config)
        
        # 2. Check educational value
        educational_score = self._evaluate_educational_value(game_config)
        
        # 3. Check age-appropriateness
        self._check_age_appropriateness(game_config, target_audience, strict_mode)
        
        # 4. Check content safety
        self._check_content_safety(game_config, strict_mode)
        
        # 5. Check cultural sensitivity
        self._check_cultural_sensitivity(game_config)
        
        # 6. AI-powered moderation (if available)
        ai_analysis = None
        if self.use_ai_moderation:
            ai_analysis = self._ai_content_analysis(game_config, target_audience)
        
        # Generate report
        report = self._generate_moderation_report(
            game_config, target_audience, educational_score, ai_analysis
        )
        
        print(f"✅ Moderation complete")
        print(f"   Violations: {len(self.violations)}")
        print(f"   Warnings: {len(self.warnings)}")
        print(f"   Educational Value: {educational_score}/100")
        
        return report
    
    def _check_structure(self, game: Dict[str, Any]):
        """Check basic game structure."""
        required_fields = ["game_id", "title", "description", "initial_state", "rounds"]
        
        for field in required_fields:
            if field not in game:
                self.violations.append({
                    "severity": "critical",
                    "type": "missing_required_field",
                    "message": f"Missing required field: '{field}'",
                    "field": field
                })
        
        # Check rounds exist
        rounds = game.get("rounds", [])
        if len(rounds) == 0:
            self.violations.append({
                "severity": "critical",
                "type": "no_rounds",
                "message": "Game has no rounds defined"
            })
    
    def _evaluate_educational_value(self, game: Dict[str, Any]) -> int:
        """Evaluate educational value (0-100)."""
        score = 50  # Base score
        
        # Check for learning objectives
        learning_objectives = game.get("learning_objectives", [])
        if learning_objectives and len(learning_objectives) > 0:
            score += 15
            if len(learning_objectives) >= 3:
                score += 5
        else:
            self.warnings.append({
                "type": "missing_learning_objectives",
                "message": "No learning objectives defined",
                "recommendation": "Add explicit learning objectives"
            })
        
        # Check for glossary
        if game.get("glossary"):
            score += 10
        
        # Check for educational content in rounds
        educational_content_count = 0
        total_text_blocks = 0
        
        for round_data in game.get("rounds", []):
            # Check story text
            story = round_data.get("story", "").lower()
            if story:
                total_text_blocks += 1
                if any(indicator in story for indicator in self.educational_indicators):
                    educational_content_count += 1
            
            # Check feedback
            for choice in round_data.get("choices", []):
                feedback = choice.get("feedback", "").lower()
                if feedback:
                    total_text_blocks += 1
                    if any(indicator in feedback for indicator in self.educational_indicators):
                        educational_content_count += 1
        
        if total_text_blocks > 0:
            educational_ratio = educational_content_count / total_text_blocks
            score += int(educational_ratio * 20)  # Up to 20 points
        
        # Check for achievements (motivation)
        if game.get("achievements") and len(game["achievements"]) >= 3:
            score += 5
        
        # Check for multiple endings (different outcomes)
        if game.get("endings") and len(game["endings"]) >= 2:
            score += 5
        
        self.educational_value_score = min(100, max(0, score))
        
        if self.educational_value_score < 50:
            self.warnings.append({
                "type": "low_educational_value",
                "message": f"Educational value score is low ({self.educational_value_score}/100)",
                "recommendation": "Add more learning objectives, glossary, and educational content"
            })
        
        return self.educational_value_score
    
    def _check_age_appropriateness(
        self,
        game: Dict[str, Any],
        target_audience: str,
        strict_mode: bool
    ):
        """Check if content is appropriate for target age."""
        # Get all text content
        text_content = self._extract_all_text(game)
        combined_text = " ".join(text_content).lower()
        
        # Check vocabulary complexity
        if target_audience in self.age_inappropriate:
            patterns = self.age_inappropriate[target_audience]
            
            for pattern in patterns:
                matches = re.findall(pattern, combined_text, re.IGNORECASE)
                if matches:
                    severity = "high" if strict_mode else "medium"
                    self.warnings.append({
                        "type": "age_inappropriate_vocabulary",
                        "severity": severity,
                        "message": f"Vocabulary may be too advanced for age group {target_audience}",
                        "examples": list(set(matches))[:3],
                        "recommendation": "Simplify language for target age group"
                    })
        
        # Check reading level (approximate)
        avg_word_length = sum(len(word) for word in combined_text.split()) / max(1, len(combined_text.split()))
        
        expected_levels = {
            "6-9": 4.5,
            "10-12": 5.5,
            "13-17": 6.5,
            "18+": 7.0
        }
        
        expected = expected_levels.get(target_audience, 6.0)
        
        if avg_word_length > expected + 1.5:
            self.warnings.append({
                "type": "reading_level_high",
                "message": f"Reading level may be too high for {target_audience} (avg word length: {avg_word_length:.1f})",
                "recommendation": "Use simpler vocabulary"
            })
    
    def _check_content_safety(self, game: Dict[str, Any], strict_mode: bool):
        """Check for inappropriate content."""
        text_content = self._extract_all_text(game)
        combined_text = " ".join(text_content).lower()
        
        # Check each inappropriate pattern
        for pattern in self.inappropriate_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            if matches:
                # Determine severity based on content type
                severity = "high" if any(word in pattern for word in ['kill', 'murder', 'sexual', 'drug']) else "medium"
                
                if strict_mode and severity == "medium":
                    severity = "high"
                
                self.violations.append({
                    "severity": severity,
                    "type": "inappropriate_content",
                    "message": f"Potentially inappropriate content detected: {list(set(matches))[:2]}",
                    "pattern": pattern,
                    "recommendation": "Review and remove or modify inappropriate content"
                })
    
    def _check_cultural_sensitivity(self, game: Dict[str, Any]):
        """Check for culturally insensitive content."""
        text_content = self._extract_all_text(game)
        combined_text = " ".join(text_content).lower()
        
        for pattern in self.culturally_sensitive_terms:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            if matches:
                self.warnings.append({
                    "type": "cultural_sensitivity",
                    "message": f"Content may be culturally sensitive: {list(set(matches))[:2]}",
                    "recommendation": "Review for stereotypes, biases, or insensitive portrayals"
                })
    
    def _extract_all_text(self, game: Dict[str, Any]) -> List[str]:
        """Extract all text content from game."""
        texts = []
        
        # Title and description
        texts.append(game.get("title", ""))
        texts.append(game.get("description", ""))
        
        # Learning objectives
        texts.extend(game.get("learning_objectives", []))
        
        # Rounds
        for round_data in game.get("rounds", []):
            texts.append(round_data.get("title", ""))
            texts.append(round_data.get("story", ""))
            
            # Choices
            for choice in round_data.get("choices", []):
                texts.append(choice.get("label", ""))
                texts.append(choice.get("feedback", ""))
            
            # Tab choices
            for tab in round_data.get("tabs", []):
                texts.append(tab.get("label", ""))
                for choice in tab.get("choices", []):
                    texts.append(choice.get("label", ""))
                    texts.append(choice.get("feedback", ""))
        
        # Endings
        for ending in game.get("endings", []):
            texts.append(ending.get("title", ""))
            texts.append(ending.get("message", ""))
        
        # Achievements
        for achievement in game.get("achievements", []):
            texts.append(achievement.get("title", ""))
            texts.append(achievement.get("description", ""))
        
        # Glossary
        for term, definition in game.get("glossary", {}).items():
            if isinstance(definition, dict):
                texts.append(definition.get("term", ""))
                texts.append(definition.get("short_definition", ""))
        
        return [t for t in texts if t]  # Remove empty strings
    
    def _ai_content_analysis(
        self,
        game: Dict[str, Any],
        target_audience: str
    ) -> Optional[Dict[str, Any]]:
        """Use AI to analyze content quality and appropriateness."""
        if not self.use_ai_moderation:
            return None
        
        print("   Using AI for advanced content analysis...")
        
        # Extract representative content
        sample_text = self._get_sample_content(game)
        
        prompt = f"""Analyze this educational game content for a {target_audience} age audience.

Game Title: {game.get('title', 'Untitled')}
Description: {game.get('description', 'No description')}
Learning Objectives: {', '.join(game.get('learning_objectives', ['None specified']))}

Sample Content:
{sample_text}

Evaluate:
1. Age-appropriateness (1-10)
2. Educational value (1-10)
3. Engagement potential (1-10)
4. Content safety concerns (list any)
5. Improvement suggestions

Respond in JSON format with these exact keys: age_appropriateness, educational_value, engagement_potential, safety_concerns, suggestions"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an educational content moderator."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            # Convert to warnings if scores are low
            if analysis.get("age_appropriateness", 10) < 6:
                self.warnings.append({
                    "type": "ai_age_concern",
                    "message": "AI detected age-appropriateness concerns",
                    "details": analysis.get("safety_concerns", [])
                })
            
            if analysis.get("educational_value", 10) < 6:
                self.warnings.append({
                    "type": "ai_educational_concern",
                    "message": "AI detected low educational value",
                    "suggestions": analysis.get("suggestions", [])
                })
            
            return analysis
            
        except Exception as e:
            print(f"   ⚠️ AI analysis failed: {e}")
            return None
    
    def _get_sample_content(self, game: Dict[str, Any]) -> str:
        """Get representative sample of game content."""
        samples = []
        
        # First 2 rounds
        for round_data in game.get("rounds", [])[:2]:
            samples.append(f"Round: {round_data.get('title', '')}")
            samples.append(round_data.get("story", ""))
            
            for choice in round_data.get("choices", [])[:2]:
                samples.append(f"- {choice.get('label', '')}")
                samples.append(f"  {choice.get('feedback', '')}")
        
        return "\n".join(samples)[:1000]  # Limit to 1000 chars
    
    def _generate_moderation_report(
        self,
        game: Dict[str, Any],
        target_audience: str,
        educational_score: int,
        ai_analysis: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate comprehensive moderation report."""
        # Determine approval status
        critical_violations = [v for v in self.violations if v.get("severity") == "critical"]
        high_violations = [v for v in self.violations if v.get("severity") == "high"]
        
        if critical_violations:
            approval_status = "rejected"
            approval_message = "Critical violations found - game cannot be published"
        elif high_violations:
            approval_status = "needs_review"
            approval_message = "High-severity issues require manual review"
        elif len(self.violations) > 0:
            approval_status = "approved_with_warnings"
            approval_message = "Approved but improvements recommended"
        elif len(self.warnings) > 3:
            approval_status = "approved_with_warnings"
            approval_message = "Approved but multiple warnings issued"
        else:
            approval_status = "approved"
            approval_message = "Game meets all moderation standards"
        
        report = {
            "game_id": game.get("game_id", "unknown"),
            "game_title": game.get("title", "Untitled"),
            "target_audience": target_audience,
            "timestamp": datetime.now().isoformat(),
            "approval_status": approval_status,
            "approval_message": approval_message,
            "scores": {
                "educational_value": educational_score,
                "safety_score": self._calculate_safety_score(),
                "age_appropriateness": self._calculate_age_appropriateness_score()
            },
            "violations": self.violations,
            "warnings": self.warnings,
            "summary": {
                "total_violations": len(self.violations),
                "critical_violations": len(critical_violations),
                "high_violations": len(high_violations),
                "medium_violations": len([v for v in self.violations if v.get("severity") == "medium"]),
                "total_warnings": len(self.warnings)
            },
            "ai_analysis": ai_analysis,
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _calculate_safety_score(self) -> int:
        """Calculate content safety score (0-100)."""
        score = 100
        
        # Deduct for violations
        for violation in self.violations:
            if violation.get("severity") == "critical":
                score -= 30
            elif violation.get("severity") == "high":
                score -= 15
            elif violation.get("severity") == "medium":
                score -= 5
        
        return max(0, score)
    
    def _calculate_age_appropriateness_score(self) -> int:
        """Calculate age-appropriateness score (0-100)."""
        score = 100
        
        # Deduct for age-related warnings
        age_warnings = [w for w in self.warnings if w.get("type") in ["age_inappropriate_vocabulary", "reading_level_high"]]
        score -= len(age_warnings) * 10
        
        return max(0, score)
    
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if self.educational_value_score < 70:
            recommendations.append("Add more educational content and clear learning objectives")
        
        if any(v.get("type") == "inappropriate_content" for v in self.violations):
            recommendations.append("Remove or modify inappropriate content")
        
        if any(w.get("type") == "age_inappropriate_vocabulary" for w in self.warnings):
            recommendations.append("Simplify vocabulary for target age group")
        
        if not any(v.get("type") == "inappropriate_content" for v in self.violations) and len(self.warnings) == 0:
            recommendations.append("Game meets all moderation standards - ready for publication")
        
        return recommendations


# Convenience functions

def moderate_game_quick(game_config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Quick function to moderate a game."""
    moderator = ContentModerator()
    return moderator.moderate_game(game_config, **kwargs)


def test_content_moderator():
    """Test content moderation."""
    print("\n" + "="*60)
    print("TESTING CONTENT MODERATION")
    print("="*60)
    
    # Test 1: Good game
    print("\n--- Test 1: Moderate good game ---")
    
    good_game = {
        "game_id": "good_game",
        "title": "Learning Adventure",
        "description": "Learn about science through exploration",
        "target_audience": "10-12",
        "learning_objectives": ["Scientific method", "Critical thinking", "Problem solving"],
        "initial_state": {"knowledge": {"value": 0, "min": 0, "max": 100}},
        "rounds": [
            {
                "id": "round_1",
                "title": "Discovery",
                "story": "You discover an interesting phenomenon. What do you do?",
                "choices": [
                    {"id": "c1", "label": "Observe carefully", "delta": {"knowledge": 10}, "feedback": "Good thinking!"},
                    {"id": "c2", "label": "Make hypothesis", "delta": {"knowledge": 15}, "feedback": "Excellent!"}
                ]
            }
        ],
        "glossary": {
            "hypothesis": {"term": "Hypothesis", "short_definition": "An educated guess"}
        },
        "achievements": [
            {"id": "a1", "title": "Scientist", "description": "Complete all experiments"}
        ],
        "endings": [
            {"id": "e1", "title": "Success", "conditions": {}}
        ]
    }
    
    moderator = ContentModerator(use_ai_moderation=False)
    report = moderator.moderate_game(good_game, target_audience="10-12")
    
    assert report["approval_status"] in ["approved", "approved_with_warnings"]
    assert report["scores"]["educational_value"] >= 50
    print(f"✅ Good game moderated: {report['approval_status']}")
    print(f"   Educational value: {report['scores']['educational_value']}/100")
    print(f"   Violations: {report['summary']['total_violations']}")
    
    # Test 2: Game with issues
    print("\n--- Test 2: Moderate problematic game ---")
    
    bad_game = {
        "game_id": "bad_game",
        "title": "Violent Game",
        "description": "Kill enemies",
        "initial_state": {"health": {"value": 100}},
        "rounds": [
            {
                "id": "round_1",
                "story": "You encounter an enemy. Kill them!",
                "choices": [
                    {"id": "c1", "label": "Attack", "delta": {"health": -10}}
                ]
            }
        ]
    }
    
    moderator2 = ContentModerator(use_ai_moderation=False)
    report2 = moderator2.moderate_game(bad_game, strict_mode=True)
    
    assert len(report2["violations"]) > 0
    print(f"✅ Problematic game moderated: {report2['approval_status']}")
    print(f"   Violations: {report2['summary']['total_violations']}")
    print(f"   Warnings: {report2['summary']['total_warnings']}")
    
    print("\n✅ ALL CONTENT MODERATION TESTS PASSED")


if __name__ == "__main__":
    test_content_moderator()
