import math

from queue import SimpleQueue


class Node:
    def __init__(self, value=1, signature=2, index=0, top=32):
        self.state = 0
        self.children = []
        self.value = value
        self.signature = signature
        self.index = index
        self.top = top
        self._create_childs()

    def _create_childs(self):
        if self.value <= self.top // self.signature:
            for i in range(self.signature):
                child = Node(
                    value=self.signature * self.value,
                    signature=self.signature,
                    index=(self.index * self.value) + i,
                    top=self.top
                )
                self.children.append(child)

    def __repr__(self):
        tree_str = ""
        q = SimpleQueue()
        explored = []
        explored.append(self)
        q.put(self)
        while not q.empty():
            node = q.get()
            tree_str += f"{node.value}/{node.signature} "
            for child in node.children:
                if child not in explored:
                    explored.append(child)
                    q.put(child)

            if node.index == node.value - 1:
                tree_str += "\n"

        return tree_str

    def __str__(self):
        return self.__repr__()


class NoteTree:
    def __init__(self, signature=None, top=32):
        if not isinstance(signature, (list, tuple)):
            self.signature = (signature, signature,)

        first_value = self.signature[1] / self.signature[0]
        self.root = Node(
            value=first_value,
            signature=signature
        )