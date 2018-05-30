import logging

from .base import BaseAction, plan, build_walker
from .base import STACK_POLL_TIME
from ..exceptions import StackDoesNotExist
from .. import util
from ..status import (
    CompleteStatus,
    FailedStatus,
    SubmittedStatus,
    SUBMITTED,
    INTERRUPTED
)

from ..status import StackDoesNotExist as StackDoesNotExistStatus

logger = logging.getLogger(__name__)

DestroyedStatus = CompleteStatus("stack destroyed")
DestroyingStatus = SubmittedStatus("submitted for destruction")
DestroyFailed = FailedStatus("stack destroy failed")


class Action(BaseAction):
    """Responsible for destroying CloudFormation stacks.

    Generates a destruction plan based on stack dependencies. Stack
    dependencies are reversed from the build action. For example, if a Stack B
    requires Stack A during build, during destroy Stack A requires Stack B be
    destroyed first.

    The plan defaults to printing an outline of what will be destroyed. If
    forced to execute, each stack will get destroyed in order.

    """

    def _generate_plan(self, tail=False):
        return plan(
            description="Destroy stacks",
            action=self._destroy_stack,
            tail=self._tail_stack if tail else None,
            stacks=self.context.get_stacks(),
            targets=self.context.stack_names,
            reverse=True)

    def _destroy_stack(self, stack, **kwargs):
        old_status = kwargs.get("status")
        wait_time = STACK_POLL_TIME if old_status == SUBMITTED else 0
        if self.cancel.wait(wait_time):
            return INTERRUPTED

        provider = self.build_provider(stack)

        try:
            provider_stack = provider.get_stack(stack.fqn)
        except StackDoesNotExist:
            logger.debug("Stack %s does not exist.", stack.fqn)
            # Once the stack has been destroyed, it doesn't exist. If the
            # status of the step was SUBMITTED, we know we just deleted it,
            # otherwise it should be skipped
            if kwargs.get("status", None) == SUBMITTED:
                return DestroyedStatus
            else:
                return StackDoesNotExistStatus()

        logger.debug(
            "Stack %s provider status: %s",
            provider.get_stack_name(provider_stack),
            provider.get_stack_status(provider_stack),
        )

        logger.debug("Destroying stack: %s", stack.fqn)

        # Below there are three checks to see if the stack has failed.
        # Unfortunately this is to handle a rather obscure corner case.
        # In order to delete a Lambda@Edge resource StackDestroy must
        # be called twice. Once without RetainResources, then again with
        # RetainResources since the stack _must_ be in a failed state for
        # RetainResources to work. The checks are there to make this
        # function idempotent across stacker destroy runs.
        #
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DeleteStack.html

        if not provider.is_stack_failed(provider_stack):
            provider.destroy_stack(provider_stack)

        if provider.is_stack_failed(provider_stack):
            retain_resources = stack.retain_resources(self.provider)
            if len(retain_resources):
                provider_stack[u'RetainResources'] = retain_resources
                provider.destroy_stack(provider_stack)
                return DestroyedStatus

        if provider.is_stack_destroyed(provider_stack):
            return DestroyedStatus

        if provider.is_stack_in_progress(provider_stack):
            return DestroyingStatus

        if provider.is_stack_failed(provider_stack):
            return DestroyFailed

        return DestroyingStatus

    def pre_run(self, outline=False, *args, **kwargs):
        """Any steps that need to be taken prior to running the action."""
        pre_destroy = self.context.config.pre_destroy
        if not outline and pre_destroy:
            util.handle_hooks(
                stage="pre_destroy",
                hooks=pre_destroy,
                provider=self.provider,
                context=self.context)

    def run(self, force, concurrency=0, tail=False, *args, **kwargs):
        plan = self._generate_plan(tail=tail)
        if force:
            # need to generate a new plan to log since the outline sets the
            # steps to COMPLETE in order to log them
            plan.outline(logging.DEBUG)
            walker = build_walker(concurrency)
            plan.execute(walker)
        else:
            plan.outline(message="To execute this plan, run with \"--force\" "
                                 "flag.")

    def post_run(self, outline=False, *args, **kwargs):
        """Any steps that need to be taken after running the action."""
        post_destroy = self.context.config.post_destroy
        if not outline and post_destroy:
            util.handle_hooks(
                stage="post_destroy",
                hooks=post_destroy,
                provider=self.provider,
                context=self.context)
