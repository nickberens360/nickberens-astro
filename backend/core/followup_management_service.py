"""
Unified service for managing categories and questions with ACID guarantees.
This service provides transactional operations for follow-up question management.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .admin_database import admin_db_manager

logger = logging.getLogger(__name__)


class FollowUpManagementService:
    """Unified service for managing categories and questions with ACID guarantees."""

    def __init__(self):
        self.db_manager = admin_db_manager

    def delete_category_with_strategy(
        self, category_id: int, strategy: str, target_category_id: Optional[int] = None, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Delete category with explicit handling of dependent questions.

        Args:
            category_id: ID of category to delete
            strategy: 'move', 'delete', or 'deactivate'
            target_category_id: Required for 'move' strategy
            user_id: User performing the operation

        Returns:
            Dictionary with operation results

        Strategies:
        - 'move': Move questions to target category
        - 'delete': Delete questions permanently
        - 'deactivate': Soft delete category, preserve questions
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Begin transaction
                cursor.execute("BEGIN TRANSACTION")

                # Validate category exists and get question count
                category = self.db_manager.get_followup_category(category_id)
                if not category:
                    raise ValueError(f"Category {category_id} not found")

                question_count = self.db_manager.get_category_question_count(category_id)

                if strategy == "move" and question_count > 0:
                    if not target_category_id:
                        raise ValueError("Target category required for move strategy")

                    # Validate target category
                    target = self.db_manager.get_followup_category(target_category_id)
                    if not target or not target["is_active"]:
                        raise ValueError("Invalid target category")

                    # Move questions
                    moved_count = self.db_manager.move_questions_to_category(category_id, target_category_id)
                    logger.info(f"Moved {moved_count} questions to category {target_category_id}")

                elif strategy == "delete" and question_count > 0:
                    # Delete all questions in category
                    cursor.execute("DELETE FROM followup_questions WHERE category_id = ?", (category_id,))
                    deleted_count = cursor.rowcount
                    logger.info(f"Deleted {deleted_count} questions from category {category_id}")

                elif strategy == "deactivate":
                    # Just deactivate category
                    success = self.db_manager.update_followup_category(category_id, is_active=False)
                    if not success:
                        raise ValueError("Failed to deactivate category")

                    # Commit and return early for deactivate
                    cursor.execute("COMMIT")
                    return {
                        "success": True,
                        "action": "deactivated",
                        "questions_preserved": question_count,
                        "category_name": category["display_name"],
                    }

                # Delete category (hard delete for move/delete strategies)
                if strategy in ["move", "delete"]:
                    success = self.db_manager.delete_followup_category(category_id)
                    if not success:
                        raise ValueError("Failed to delete category")

                # Commit transaction
                cursor.execute("COMMIT")

                return {
                    "success": True,
                    "action": strategy,
                    "questions_affected": question_count,
                    "target_category_id": target_category_id if strategy == "move" else None,
                    "category_name": category["display_name"],
                }

        except Exception as e:
            # Rollback on error
            try:
                cursor.execute("ROLLBACK")
            except:
                pass
            logger.error(f"Error deleting category {category_id}: {str(e)}")
            raise

    def bulk_update_questions(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform bulk operations on questions.

        Args:
            operations: List of operation dictionaries with 'action', 'question_id', etc.

        Returns:
            Dictionary with results summary
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("BEGIN TRANSACTION")

                results = {"success": True, "operations_completed": 0, "operations_failed": 0, "errors": []}

                for operation in operations:
                    try:
                        action = operation.get("action")
                        question_id = operation.get("question_id")

                        if action == "delete":
                            success = self.db_manager.delete_followup_question(question_id)
                        elif action == "activate":
                            success = self.db_manager.update_followup_question(question_id, is_active=True)
                        elif action == "deactivate":
                            success = self.db_manager.update_followup_question(question_id, is_active=False)
                        elif action == "update":
                            success = self.db_manager.update_followup_question(
                                question_id,
                                question_text=operation.get("question_text"),
                                sort_order=operation.get("sort_order"),
                            )
                        else:
                            raise ValueError(f"Unknown action: {action}")

                        if success:
                            results["operations_completed"] += 1
                        else:
                            results["operations_failed"] += 1
                            results["errors"].append(f"Operation failed for question {question_id}")

                    except Exception as e:
                        results["operations_failed"] += 1
                        results["errors"].append(f"Error in operation: {str(e)}")

                cursor.execute("COMMIT")
                return results

        except Exception as e:
            try:
                cursor.execute("ROLLBACK")
            except:
                pass
            logger.error(f"Error in bulk operations: {str(e)}")
            raise

    def reorder_questions_in_category(self, category_id: int, question_orders: List[Dict[str, int]]) -> bool:
        """
        Reorder questions within a category.

        Args:
            category_id: Category to reorder questions in
            question_orders: List of {question_id, sort_order} dictionaries
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("BEGIN TRANSACTION")

                for item in question_orders:
                    cursor.execute(
                        """
                        UPDATE followup_questions 
                        SET sort_order = ?, updated_at = ? 
                        WHERE id = ? AND category_id = ?
                        """,
                        (item["sort_order"], datetime.now(), item["question_id"], category_id),
                    )

                cursor.execute("COMMIT")
                logger.info(f"Reordered {len(question_orders)} questions in category {category_id}")
                return True

        except Exception as e:
            try:
                cursor.execute("ROLLBACK")
            except:
                pass
            logger.error(f"Error reordering questions: {str(e)}")
            return False

    def get_category_with_questions(self, category_id: int) -> Optional[Dict[str, Any]]:
        """Get category with its questions included."""
        try:
            category = self.db_manager.get_followup_category(category_id)
            if not category:
                return None

            questions = self.db_manager.get_followup_questions(category_id=category_id)
            category["questions"] = questions
            category["questions_count"] = len(questions)

            return category
        except Exception as e:
            logger.error(f"Error getting category with questions: {str(e)}")
            return None

    def search_questions(self, query: str, category_id: Optional[int] = None, limit: int = 20) -> List[Dict]:
        """Full-text search across questions."""
        try:
            return self.db_manager.get_followup_questions(category_id=category_id, search=query, limit=limit)
        except Exception as e:
            logger.error(f"Error searching questions: {str(e)}")
            return []

    def get_categories_with_stats(self) -> List[Dict[str, Any]]:
        """Get all categories with question counts and usage stats."""
        try:
            categories = self.db_manager.get_followup_categories(active_only=False)

            for category in categories:
                category["questions_count"] = self.db_manager.get_category_question_count(category["id"])
                # Add more stats as needed (usage counts, etc.)

            return categories
        except Exception as e:
            logger.error(f"Error getting categories with stats: {str(e)}")
            return []

    def validate_category_deletion(self, category_id: int) -> Dict[str, Any]:
        """
        Validate if a category can be safely deleted and provide options.

        Returns:
            Dictionary with validation results and available options
        """
        try:
            category = self.db_manager.get_followup_category(category_id)
            if not category:
                return {"valid": False, "error": "Category not found"}

            question_count = self.db_manager.get_category_question_count(category_id)

            # Get available target categories for move operation
            target_categories = [
                cat
                for cat in self.db_manager.get_followup_categories()
                if cat["id"] != category_id and cat["is_active"]
            ]

            return {
                "valid": True,
                "category": category,
                "questions_count": question_count,
                "can_delete_directly": question_count == 0,
                "available_strategies": {"move": len(target_categories) > 0, "delete": True, "deactivate": True},
                "target_categories": target_categories,
            }

        except Exception as e:
            logger.error(f"Error validating category deletion: {str(e)}")
            return {"valid": False, "error": str(e)}


# Global instance
followup_management_service = FollowUpManagementService()
