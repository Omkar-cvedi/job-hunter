import re

class ProfileMatcher:
    def __init__(self, config):
        self.config = config
        self.candidate = config.get("candidate", {})
        self.skills = self.candidate.get("skills", {})
        self.hard_negatives = config.get("hard_negatives", [])
        self.open_locations = [loc.lower() for loc in self.candidate.get("open_locations", [])]
        self.scoring_weights = config.get("scoring_weights", {
            "core_java": 20,
            "spring_framework": 30,
            "database": 15,
            "cloud_devops": 15,
            "testing_tools": 10,
            "engineering_dsa": 10
        })

    def check_hard_negatives(self, title, description=""):
        """Checks if the title or description triggers any hard negative keywords."""
        full_text = f"{title.lower()} {description.lower()}"
        
        # Immediate title-level exclusions
        title_lower = title.lower()
        strict_title_negatives = [
            "python", "fastapi", "django", "flask",
            "react", "angular", "vue", "frontend", "front end", "ui developer",
            "golang", "ruby", "ios", "android", "flutter",
            "senior", "sr.", "lead", "staff", "principal", "manager", "director", "architect"
        ]
        for neg in strict_title_negatives:
            # Match word boundary
            if re.search(r'\b' + re.escape(neg) + r'\b', title_lower):
                return True, f"Excluded by role title keyword: '{neg}'"

        # Explicit experience in title e.g. (4-12+ yrs), 3+ yrs, 5-8 years
        title_exp_match = re.search(r'(?:[^\d]|^)([3-9]|\d{2})\s*(?:-|to|\+)\s*(?:\d+)?\s*\+?\s*(?:yrs?|years?)', title_lower)
        if title_exp_match:
            return True, f"Excluded by high experience in title: {title_exp_match.group(0).strip()}"

        # Experience-based negative exclusions in description
        experience_negatives = [
            r'([4-9]|\d{2})\+?\s*(?:to|-)?\s*\d*\s*years?\s*(?:of)?\s*experience',
            r'(?:minimum|at\s*least)\s*([4-9]|\d{2})\s*years?',
            r'experience\s*:\s*([4-9]|\d{2})\+?\s*years?'
        ]
        for pattern in experience_negatives:
            match = re.search(pattern, full_text)
            if match:
                return True, f"Excluded by high experience requirement ({match.group(0)})"

        return False, None

    def evaluate(self, title, company, location, description=""):
        """Evaluates a job against the profile and returns match details."""
        rejected, reason = self.check_hard_negatives(title, description)
        if rejected:
            return {
                "qualified": False,
                "rejection_reason": reason,
                "match_percentage": 0,
                "matched_skills": [],
                "missing_skills": []
            }

        text = f"{title} {description}".lower()
        category_scores = {}
        all_matched_skills = []
        all_missing_skills = []

        total_weight = sum(self.scoring_weights.values())
        achieved_score = 0.0

        for category, skill_list in self.skills.items():
            cat_weight = self.scoring_weights.get(category, 10)
            matched_in_cat = []
            missing_in_cat = []

            for skill in skill_list:
                # Use regex with boundary or exact term
                pattern = r'\b' + re.escape(skill.lower()) + r'\b'
                if re.search(pattern, text):
                    matched_in_cat.append(skill)
                else:
                    missing_in_cat.append(skill)

            matched_count = len(matched_in_cat)
            if matched_count >= 3:
                cat_score = cat_weight * 1.0
            elif matched_count == 2:
                cat_score = cat_weight * 0.8
            elif matched_count == 1:
                cat_score = cat_weight * 0.55
            else:
                cat_score = 0.0

            achieved_score += cat_score
            category_scores[category] = cat_score
            all_matched_skills.extend(matched_in_cat)
            all_missing_skills.extend(missing_in_cat)

        # Baseline bonus if title explicitly mentions Java / Spring / Backend
        title_lower = title.lower()
        title_bonus = 0
        if "java" in title_lower and ("backend" in title_lower or "spring" in title_lower or "developer" in title_lower):
            title_bonus += 15
        elif "java" in title_lower:
            title_bonus += 10
        elif "backend" in title_lower or "back end" in title_lower:
            title_bonus += 8

        if "fresher" in title_lower or "intern" in title_lower or "entry level" in title_lower or "associate" in title_lower or "junior" in title_lower or "sde 1" in title_lower or "sde-1" in title_lower:
            title_bonus += 8

        # Check location compatibility
        loc_lower = location.lower()
        is_location_compatible = False
        for target_loc in self.open_locations:
            if target_loc in loc_lower:
                is_location_compatible = True
                break
        
        # If location is generally in India or Remote, count as compatible
        if "india" in loc_lower or "remote" in loc_lower or not location.strip():
            is_location_compatible = True

        raw_percentage = (achieved_score / total_weight) * 75 + title_bonus
        final_percentage = min(98, max(25, int(round(raw_percentage))))

        # High priority skills highlight
        priority_skills = ["java", "spring boot", "spring security", "jwt", "mysql", "rest api", "aws", "microservices"]
        highlighted_matched = [s for s in all_matched_skills if s in priority_skills]
        highlighted_missing = [s for s in priority_skills if s not in all_matched_skills]

        return {
            "qualified": True,
            "match_percentage": final_percentage,
            "category_scores": category_scores,
            "matched_skills": sorted(list(set(highlighted_matched or all_matched_skills[:8]))),
            "missing_skills": sorted(list(set(highlighted_missing[:4]))),
            "is_location_compatible": is_location_compatible
        }
