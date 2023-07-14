import d20
from d20 import Expression, Stringifier, Dice
from d20.dice import RollResult, ASTNode, CritType


class D10_RollResult(RollResult):
    """
    Holds information about the result of a roll. This should generally not be constructed manually.
    """

    def __init__(self, the_ast: ASTNode, the_roll: Expression, stringifier: Stringifier):
        super().__init__(the_ast, the_roll, stringifier)

    @property
    def crit(self) -> CritType:
        """
        If the leftmost node was Xd20kh1, returns :class:`CritType.CRIT` if the roll was a 20 and
        :class:`CritType.FAIL` if the roll was a 1.
        Returns :class:`CritType.NONE` otherwise.

        :rtype: CritType
        """
        # find the left most node in the dice expression
        left = self.expr
        while left.children:
            left = left.children[0]

        # ensure the node is dice
        if not isinstance(left, Dice):
            return CritType.NONE

        # ensure only one die of size 20 is kept
        if not (len(left.keptset) == 1 and left.size == 10):
            return CritType.NONE

        if left.total == 1:
            return CritType.FAIL
        elif left.total == 10:
            return CritType.CRIT
        return CritType.NONE


def d20_to_d10(roll: d20.RollResult):
    d10_result = D10_RollResult(
        the_ast=roll.ast,
        the_roll=roll.expr,
        stringifier=roll.stringifier,
    )
    return d10_result
