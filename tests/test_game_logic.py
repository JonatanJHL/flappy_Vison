import unittest
import sys
import os
import pygame

# Set dummy video driver for headless testing
os.environ['SDL_VIDEODRIVER'] = 'dummy'

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from main import Bird, PowerUp, SCREEN_HEIGHT, SCREEN_WIDTH, GRAVITY, FLAP_STRENGTH

class TestBirdMechanics(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.bird_p1 = Bird(55, 300, color_scheme=1)  # Player 1 (Yellow)
        self.bird_p2 = Bird(55, 300, color_scheme=2)  # Player 2 (Blue)

    def test_initial_state(self):
        self.assertEqual(self.bird_p1.lives, 3)
        self.assertEqual(self.bird_p1.state, Bird.STATE_ALIVE)
        self.assertEqual(self.bird_p1.body_color, (255, 220, 0))

        self.assertEqual(self.bird_p2.lives, 3)
        self.assertEqual(self.bird_p2.body_color, (70, 130, 255))

    def test_flap_strength(self):
        # Strong flap (Fist gesture)
        self.bird_p1.flap(strength=0)
        self.assertEqual(self.bird_p1.velocity, -10)

        # Gentle flap (Semi gesture)
        self.bird_p1.flap(strength=1)
        self.assertEqual(self.bird_p1.velocity, -6)

        # Standard flap
        self.bird_p1.flap(strength=2)
        self.assertEqual(self.bird_p1.velocity, FLAP_STRENGTH)

    def test_shield_and_hit_logic(self):
        # Activate shield
        self.bird_p1.activate_shield(duration=100)
        self.assertEqual(self.bird_p1.state, Bird.STATE_SHIELD)

        # Hit while shielded should consume shield without losing lives
        murió = self.bird_p1.take_hit()
        self.assertFalse(murió)
        self.assertEqual(self.bird_p1.lives, 3)
        self.assertEqual(self.bird_p1.state, Bird.STATE_ALIVE)

        # Taking hits until dead
        self.bird_p1.take_hit()  # Lives -> 2, hurt
        self.assertEqual(self.bird_p1.lives, 2)
        
        # Reset hurt state for testing
        self.bird_p1.state = Bird.STATE_ALIVE
        self.bird_p1.take_hit()  # Lives -> 1
        self.assertEqual(self.bird_p1.lives, 1)

        self.bird_p1.state = Bird.STATE_ALIVE
        dead = self.bird_p1.take_hit()  # Lives -> 0, dead
        self.assertTrue(dead)
        self.assertEqual(self.bird_p1.state, Bird.STATE_DEAD)


class TestPowerUpMechanics(unittest.TestCase):
    def test_powerup_initialization(self):
        pu = PowerUp(100, 200, PowerUp.TYPE_SHIELD)
        self.assertEqual(pu.kind, PowerUp.TYPE_SHIELD)
        self.assertFalse(pu.collected)
        
        rect = pu.get_rect()
        self.assertTrue(isinstance(rect, pygame.Rect))

    def test_powerup_movement(self):
        pu = PowerUp(100, 200, PowerUp.TYPE_SLOW)
        pu.update(pipe_speed=4)
        self.assertEqual(pu.x, 96)


class TestPlayerAssignmentLogic(unittest.TestCase):
    def test_hand_position_splitting(self):
        # Simulated hand landmarks positions (normalized X)
        hands_mock = [
            {'x_pos': 0.2, 'state': 0},  # Left hand -> Player 1 Fist
            {'x_pos': 0.8, 'state': 1},  # Right hand -> Player 2 Semi
        ]

        player_states = [2, 2]  # Default open
        for hand in hands_mock:
            if hand['x_pos'] < 0.5:
                player_states[0] = hand['state']
            else:
                player_states[1] = hand['state']

        self.assertEqual(player_states[0], 0)  # P1 got Fist (0)
        self.assertEqual(player_states[1], 1)  # P2 got Semi (1)


if __name__ == '__main__':
    unittest.main()
