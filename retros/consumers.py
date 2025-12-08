import json
from channels.generic.websocket import AsyncWebsocketConsumer

class BoardConsumer(AsyncWebsocketConsumer):
    """
    Websocket consumer for real time board updates
    Each board has its own 'room' so only users viewing the board get updates
    """

    async def connect(self):
        """Called when a websocket connection is opened"""
        self.board_id = self.scope['url_route']['kwargs']['board_id']
        self.room_group_name = f'board_{self.board_id}'

        # join the room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        """Called when websocket is closed"""
        # leave the room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Called when a message is received from websocket"""

        pass

    # event handlers - called when views broadcast events

    # TEAM (through board)

    async def team_updated(self, event):
        await self.send(text_data=json.dumps(event))

    # BOARD

    async def board_updated(self, event):
        await self.send(text_data=json.dumps(event))

    # COLUMNS

    async def column_created(self, event):
        await self.send(text_data=json.dumps(event))

    async def column_updated(self, event):
        await self.send(text_data=json.dumps(event))

    async def column_deleted(self, event):
        await self.send(text_data=json.dumps(event))

    # CARDS

    async def card_created(self, event):
        """Send card created event to websocket"""
        await self.send(text_data=json.dumps(event))

    async def card_updated(self, event):
        await self.send(text_data=json.dumps(event))

    async def card_deleted(self, event):
        await self.send(text_data=json.dumps(event))

    async def card_moved(self, event):
        await self.send(text_data=json.dumps(event))

    # ACTION ITEMS

    async def action_item_created(self, event):
        await self.send(text_data=json.dumps(event))

    async def action_item_updated(self, event):
        await self.send(text_data=json.dumps(event))

    async def action_item_deleted(self, event):
        await self.send(text_data=json.dumps(event))

    # VOTES
    async def card_voted(self, event):
        """Send card voted event to websocket"""
        await self.send(text_data=json.dumps(event))

    async def voting_round_started(self, event):
        """Send voting round started event to websocket"""
        await self.send(text_data=json.dumps(event))

    async def voting_stopped(self, event):
        """Send voting stopped event to websocket"""
        await self.send(text_data=json.dumps(event))

    async def voting_reset(self, event):
        """Send voting reset event to websocket"""
        await self.send(text_data=json.dumps(event))