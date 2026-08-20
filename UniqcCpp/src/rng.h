#pragma once
#include <random>

namespace uniqc
{
	namespace detail
	{
		// One engine per thread, so rand()/seed() need no locking.
		// Each thread's engine is seeded from std::random_device by default;
		// calling uniqc::seed() reseeds only the calling thread's engine,
		// making its subsequent rand() sequence reproducible.
		inline std::mt19937_64& thread_engine()
		{
			thread_local std::mt19937_64 eng{ std::random_device{}() };
			return eng;
		}
	}

	inline double rand()
	{
		static thread_local std::uniform_real_distribution<double> dist;
		return dist(detail::thread_engine());
	}

	inline void seed(unsigned int seed_)
	{
		detail::thread_engine().seed(seed_);
	}
}
