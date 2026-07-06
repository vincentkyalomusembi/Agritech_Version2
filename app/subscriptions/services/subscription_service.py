from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.subscriptions.exceptions import FarmerNotFoundError
from app.subscriptions.model import Subscription
from app.subscriptions.repository import SubscriptionRepository
from app.subscriptions.schema import SubscriptionResponse
from app.farmers.repository import FarmerRepository

DEFAULT_PLAN_NAME = "Premium"
DEFAULT_SUBSCRIPTION_DAYS = 30


class SubscriptionService:
    """
    Reusable subscription business logic.

    Intended for use by USSD flows, recommendations, and admin tools.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = SubscriptionRepository(db)
        self.farmer_repository = FarmerRepository(db)

    def _ensure_farmer_exists(self, farmer_id: UUID) -> None:
        """Validate that the farmer exists."""

        if self.farmer_repository.get_by_id(farmer_id) is None:
            raise FarmerNotFoundError()

    def _resolve_dates(
        self,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[date, date]:
        """Apply defaults for subscription date ranges."""

        resolved_start = start_date or date.today()
        resolved_end = end_date or (
            resolved_start + timedelta(days=DEFAULT_SUBSCRIPTION_DAYS)
        )

        return resolved_start, resolved_end

    def activate_subscription(
        self,
        farmer_id: UUID,
        plan_name: str = DEFAULT_PLAN_NAME,
        start_date: date | None = None,
        end_date: date | None = None,
        *,
        commit: bool = True,
    ) -> SubscriptionResponse:
        """Activate or overwrite a farmer's premium subscription."""

        self._ensure_farmer_exists(farmer_id)
        resolved_start, resolved_end = self._resolve_dates(
            start_date,
            end_date,
        )

        if resolved_end < resolved_start:
            raise ValueError("end_date cannot be earlier than start_date.")

        try:
            subscription = self.repository.get_by_farmer_id(farmer_id)

            if subscription is None:
                subscription = Subscription(
                    farmer_id=farmer_id,
                    is_active=True,
                    plan_name=plan_name,
                    start_date=resolved_start,
                    end_date=resolved_end,
                )
                try:
                    self.repository.create(subscription)
                except IntegrityError:
                    self.db.rollback()
                    subscription = self.repository.get_by_farmer_id(farmer_id)
                    if subscription is None:
                        raise
                    subscription.is_active = True
                    subscription.plan_name = plan_name
                    subscription.start_date = resolved_start
                    subscription.end_date = resolved_end
                    self.repository.update(subscription)
            else:
                subscription.is_active = True
                subscription.plan_name = plan_name
                subscription.start_date = resolved_start
                subscription.end_date = resolved_end
                self.repository.update(subscription)

            if commit:
                self.db.commit()

            self.db.refresh(subscription)

            return SubscriptionResponse.model_validate(subscription)

        except Exception:
            self.db.rollback()
            raise

    def deactivate_subscription(
        self,
        farmer_id: UUID,
        *,
        commit: bool = True,
    ) -> SubscriptionResponse:
        """Deactivate a farmer's premium subscription."""

        self._ensure_farmer_exists(farmer_id)

        subscription = self.repository.get_by_farmer_id(farmer_id)
        if subscription is None:
            subscription = Subscription(
                farmer_id=farmer_id,
                is_active=False,
                plan_name=DEFAULT_PLAN_NAME,
            )
            created = self.repository.create(subscription)

            if commit:
                self.db.commit()

            self.db.refresh(created)

            return SubscriptionResponse.model_validate(created)

        try:
            subscription.is_active = False
            updated = self.repository.update(subscription)

            if commit:
                self.db.commit()

            return SubscriptionResponse.model_validate(updated)

        except Exception:
            self.db.rollback()
            raise

    def validate_expiration(
        self,
        farmer_id: UUID,
        *,
        commit: bool = True,
    ) -> SubscriptionResponse | None:
        """
        Deactivate expired subscriptions and return the current record.

        Returns None when no subscription exists.
        """

        subscription = self.repository.get_by_farmer_id(farmer_id)
        if subscription is None:
            return None

        if (
            subscription.is_active
            and subscription.end_date is not None
            and subscription.end_date < date.today()
        ):
            try:
                subscription.is_active = False
                updated = self.repository.update(subscription)

                if commit:
                    self.db.commit()

                return SubscriptionResponse.model_validate(updated)

            except Exception:
                self.db.rollback()
                raise

        return SubscriptionResponse.model_validate(subscription)

    def is_premium_active(self, farmer_id: UUID) -> bool:
        """
        Check whether a farmer currently has premium access.

        Automatically deactivates expired subscriptions.
        """

        subscription = self.validate_expiration(farmer_id)
        if subscription is None:
            return False

        return subscription.is_active

    def renew_subscription(
        self,
        farmer_id: UUID,
        end_date: date | None = None,
        plan_name: str = DEFAULT_PLAN_NAME,
        *,
        commit: bool = True,
    ) -> SubscriptionResponse:
        """Extend or restart a farmer's premium subscription."""

        self._ensure_farmer_exists(farmer_id)

        subscription = self.repository.get_by_farmer_id(farmer_id)
        start_date = date.today()

        if subscription is not None and subscription.end_date is not None:
            if subscription.end_date >= date.today():
                start_date = subscription.end_date

        return self.activate_subscription(
            farmer_id=farmer_id,
            plan_name=plan_name,
            start_date=start_date,
            end_date=end_date,
            commit=commit,
        )
