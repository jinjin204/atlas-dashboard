
import sys
import os
import json

# Add path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic import zeus_chat

# Mock data with process times
mock_master = [
    {
        "id": "SW_LEGE_L_BDY", "name": "伝説剣　長", "part": "本体", "category": "剣", 
        "target_quantity": 11, "current_stock": 6, "remaining": 5,
        "process": {"nc": {"front_rough_min": 30, "front_finish_min": 20}, "manual": {"sanding_min": 60}}
    },
    {
        "id": "SW_LEGE_L_SCB", "name": "伝説剣　長", "part": "鞘", "category": "剣", 
        "target_quantity": 11, "current_stock": 6, "remaining": 5,
        "process": {"nc": {"front_rough_min": 20, "front_finish_min": 10}, "manual": {"sanding_min": 30}}
    },
    {
        "id": "SW_LEGE_S_BDY", "name": "伝説剣　短", "part": "本体", "category": "剣", 
        "target_quantity": 10, "current_stock": 2, "remaining": 8,
        "process": {"nc": {"front_rough_min": 15, "front_finish_min": 15}, "manual": {"sanding_min": 45}}
    },
    {
        "id": "AX_AXE_L_BDY", "name": "斧　大", "part": "本体", "category": "斧", 
        "target_quantity": 5, "current_stock": 1, "remaining": 4,
        "process": {"nc": {"front_rough_min": 60, "front_finish_min": 60}, "manual": {"sanding_min": 90}}
    }
]

def test_search(query):
    print(f"\n--- Testing Query: '{query}' ---")
    hits = zeus_chat.search_products_by_query(mock_master, query)
    print(f"Hits: {len(hits)}")
    for h in hits:
        print(f" - {h['name']} ({h['part']})")
    
    if hits:
        context = zeus_chat.build_search_context(hits)
        print("\n[Generated Context]")
        print(context)

def main():
    test_search("伝説剣")
    test_search("斧")
    test_search("在庫") # Should be ignored or handle carefully
    test_search("剣")

if __name__ == "__main__":
    main()
