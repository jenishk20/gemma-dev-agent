class Click < ApplicationRecord
  # The schema requires id and timestamp. 
  # Rails provides id by default. 
  # We ensure timestamp is present.
  validates :timestamp, presence: true
end