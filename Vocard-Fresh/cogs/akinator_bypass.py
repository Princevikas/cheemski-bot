"""
Akinator bypass using curl_cffi as a drop-in replacement for cloudscraper.
This patches the akinator library to use curl_cffi for better Cloudflare bypass.
"""
import akinator
from curl_cffi import requests as curl_requests


class CurlSession:
    """
    A wrapper that makes curl_cffi.requests compatible with cloudscraper's interface.
    """
    def __init__(self):
        self._session = curl_requests.Session(impersonate="chrome110")
    
    def get(self, url, **kwargs):
        # Remove cloudscraper-specific params
        kwargs.pop('browser', None)
        kwargs.pop('platform', None)
        kwargs.pop('mobile', None)
        
        # Ensure timeout is set
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30
            
        return self._session.get(url, **kwargs)
    
    def post(self, url, **kwargs):
        kwargs.pop('browser', None)
        kwargs.pop('platform', None)
        kwargs.pop('mobile', None)
        
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30
            
        return self._session.post(url, **kwargs)
    
    def close(self):
        try:
            self._session.close()
        except:
            pass


def create_akinator_with_bypass(child_mode: bool = True) -> akinator.Akinator:
    """
    Create an Akinator instance with curl_cffi bypass.
    This patches the internal session to use curl_cffi instead of cloudscraper.
    """
    aki = akinator.Akinator()
    
    # Replace the internal session with our curl_cffi wrapper
    # The akinator library stores the session in aki.session
    aki.session = CurlSession()
    
    return aki


# Test if it works
if __name__ == "__main__":
    print("Testing Akinator with curl_cffi bypass...")
    
    try:
        aki = create_akinator_with_bypass(child_mode=True)
        print("Starting game...")
        aki.start_game(child_mode=True)
        
        print(f"✅ Game started!")
        print(f"Question: {aki.question}")
        print(f"Step: {aki.step}")
        
        # Answer a few questions
        for i in range(5):
            print(f"\nStep {aki.step}: Answering 'yes'...")
            aki.answer("yes")
            print(f"Next question: {aki.question[:50]}...")
            print(f"Progression: {aki.progression:.1f}%")
            
            if aki.finished:
                print(f"\n✅ Akinator ready to guess!")
                print(f"Guess: {aki.name_proposition}")
                break
        
        print("\n✅ TEST PASSED!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
