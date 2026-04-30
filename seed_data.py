"""
Seed Database Script for ElevatorAI
Creates sample cabin designs and initializes the database
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from shared.models import init_database, Base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from shared.models import Customer, CabinDesign, DesignSession, Quote, WhatsAppMessage
import json


def create_cabin_designs(session):
    """Create sample elevator cabin designs"""
    
    cabins = [
        CabinDesign(
            id="classic-001",
            name="Imperial Gold",
            style_tags=["Luxury Classic", "Art Deco"],
            materials=["Polished Gold", "White Marble", "Mirror"],
            color_palette={"dominant": ["#FFD700", "#FFFFFF", "#333333"], "accent": ["#C0A050"]},
            price_usd=45000.0,
            dimensions={"width": 1.4, "depth": 1.6, "height": 2.5},
            capacity=8,
            features=["Handcrafted Gold Leaf", "Marble Flooring", "Smart Lighting", "Crystal Chandelier"],
            thumbnail_url="static/thumbnails/imperial_gold.jpg",
            description="A luxurious classic elevator cabin with handcrafted gold leaf details and Italian marble flooring. Perfect for palatial villas and high-end residences."
        ),
        CabinDesign(
            id="modern-001",
            name="Skyline Minimalist",
            style_tags=["Modern Minimalist", "High-Tech"],
            materials=["Brushed Steel", "Clear Glass", "Concrete"],
            color_palette={"dominant": ["#727375", "#F5F5F7", "#000000"], "accent": ["#4A90D9"]},
            price_usd=32000.0,
            dimensions={"width": 1.2, "depth": 1.4, "height": 2.4},
            capacity=6,
            features=["Panoramic Glass", "Integrated LED", "Touch Control", "Anti-Fingerprint Coating"],
            thumbnail_url="static/thumbnails/skyline_min.jpg",
            description="Sleek minimalist design with panoramic glass walls and integrated LED lighting. Ideal for contemporary urban villas."
        ),
        CabinDesign(
            id="nature-001",
            name="Biophilic Sanctuary",
            style_tags=["Biophilic", "Scandinavian"],
            materials=["Oak Wood", "Linen", "Matte Black Steel"],
            color_palette={"dominant": ["#655035", "#F5F5DC", "#2D5A27"], "accent": ["#8B7355"]},
            price_usd=38000.0,
            dimensions={"width": 1.5, "depth": 1.7, "height": 2.5},
            capacity=10,
            features=["Living Wall Option", "Natural Wood Finishes", "Soft Acoustic Panels", "Air Purification"],
            thumbnail_url="static/thumbnails/biophilic.jpg",
            description="Bring nature indoors with this biophilic design featuring natural oak wood and optional living moss walls. Creates a calming, spa-like experience."
        ),
        CabinDesign(
            id="industrial-001",
            name="Urban Loft",
            style_tags=["Industrial Loft", "Contemporary"],
            materials=["Black Iron", "Reclaimed Wood", "Exposed Steel"],
            color_palette={"dominant": ["#2C2C2C", "#8B6914", "#444444"], "accent": ["#FF6B35"]},
            price_usd=28000.0,
            dimensions={"width": 1.3, "depth": 1.5, "height": 2.6},
            capacity=6,
            features=["Exposed Rivet Details", "Vintage Controls", "Edison Bulb Lighting", "Leather Handrail"],
            thumbnail_url="static/thumbnails/urban_loft.jpg",
            description="Raw industrial aesthetics with exposed ironwork and reclaimed barn wood. Perfect for loft-style apartments and industrial-themed homes."
        ),
        CabinDesign(
            id="zen-001",
            name="Japanese Zen",
            style_tags=["Japanese Zen", "Minimalist"],
            materials=["Bamboo", "Stone", "Rice Paper"],
            color_palette={"dominant": ["#E8DCC8", "#8B7355", "#F5F5F0"], "accent": ["#C41E3A"]},
            price_usd=35000.0,
            dimensions={"width": 1.4, "depth": 1.4, "height": 2.3},
            capacity=4,
            features=["Shoji Screen Panels", "Stone Floor Inlay", "Zen Garden View", "Silent Operation"],
            thumbnail_url="static/thumbnails/japanese_zen.jpg",
            description="Meditative simplicity with shoji-inspired screens and natural stone elements. Creates a serene transition between floors."
        ),
        CabinDesign(
            id="artdeco-001",
            name="Gatsby Glamour",
            style_tags=["Art Deco", "Luxury"],
            materials=["Brass", "Mahogany", "Velvet", "Mirror"],
            color_palette={"dominant": ["#1A1A2E", "#D4AF37", "#8B4513"], "accent": ["#FF1493"]},
            price_usd=52000.0,
            dimensions={"width": 1.6, "depth": 1.8, "height": 2.7},
            capacity=8,
            features=["Geometric Brass Inlays", "Velvet Bench Seating", "Art Deco Chandelier", "Mirrored Ceiling"],
            thumbnail_url="static/thumbnails/gatsby_glamour.jpg",
            description="Roaring twenties glamour with geometric brass patterns and rich mahogany. A statement piece for grand residences."
        ),
        CabinDesign(
            id="coastal-001",
            name="Mediterranean Breeze",
            style_tags=["Coastal", "Mediterranean"],
            materials=["White Oak", "Rope", "Glass", "Terrazzo"],
            color_palette={"dominant": ["#FFFFFF", "#006994", "#E8DCC8"], "accent": ["#F4A460"]},
            price_usd=30000.0,
            dimensions={"width": 1.4, "depth": 1.6, "height": 2.5},
            capacity=6,
            features=["Nautical Rope Details", "Terrazzo Flooring", "Ocean View Glass", "Weathered Brass Fixtures"],
            thumbnail_url="static/thumbnails/mediterranean.jpg",
            description="Light and airy coastal design with nautical touches and natural textures. Brings seaside villa charm indoors."
        ),
        CabinDesign(
            id="hitech-001",
            name="Future Flow",
            style_tags=["High-Tech", "Modern"],
            materials=["Carbon Fiber", "Smart Glass", "Aluminum"],
            color_palette={"dominant": ["#000000", "#00FF88", "#1A1A1A"], "accent": ["#00CCFF"]},
            price_usd=55000.0,
            dimensions={"width": 1.5, "depth": 1.6, "height": 2.5},
            capacity=8,
            features=["Smart Glass Walls", "Holographic Controls", "Voice Activation", "Biometric Access", "Air Purification"],
            thumbnail_url="static/thumbnails/future_flow.jpg",
            description="Cutting-edge technology meets luxury. Features smart glass that turns opaque at the touch of a button and holographic control panels."
        ),
    ]
    
    for cabin in cabins:
        # Check if already exists
        existing = session.query(CabinDesign).filter_by(id=cabin.id).first()
        if not existing:
            session.add(cabin)
            print(f"  Added cabin: {cabin.name}")
        else:
            print(f"  Cabin exists: {cabin.name}")
    
    session.commit()
    print(f"\nTotal cabins in database: {session.query(CabinDesign).count()}")


def init_and_seed():
    """Initialize database and seed with sample data"""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Please set it in your .env file or environment")
        sys.exit(1)
    
    print(f"Connecting to database...")
    print(f"Creating tables...")
    
    Session = init_database(database_url)
    session = Session()
    
    print("Seeding cabin designs...")
    create_cabin_designs(session)
    
    session.close()
    print("\nDone! Database is ready.")


if __name__ == "__main__":
    init_and_seed()
